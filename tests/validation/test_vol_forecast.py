"""
Tests for the volatility forecaster and its walk-forward evaluation.

Seeded synthetic series test the MACHINERY (alignment, gap safety, purging,
metrics). They say nothing about any real market.
"""

import math
import random

from src.analysis.volatility import (
    BASE_FEATURES,
    VolatilityError,
    VolatilityForecaster,
    VolatilityTable,
    build_table,
)
from src.analysis.volatility.forecaster import ewma, time_features
from src.domain.models import Candle
from src.validation.vol_walkforward import (
    calibration_slope,
    coverage,
    decile_table,
    mse,
    rising_steps,
    walk_forward,
    yearly_comparison,
)

HOUR = 3_600_000


def candle(open_, high, low, close, ts=0):
    return Candle(
        timestamp=ts, open=open_, high=high, low=low, close=close,
        volume=0, quote_volume=0, trades=0, buy_volume=0, buy_quote_volume=0,
    )


def walk(n, seed, start_ts=0, vol=0.004):
    rng = random.Random(seed)
    price = 1000.0
    var = vol * vol
    out = []
    for i in range(n):
        open_ = price
        r = rng.gauss(0.0, math.sqrt(var))
        var = 0.0000012 + 0.08 * r * r + 0.90 * var
        price = open_ * (1.0 + r)
        spread = abs(math.sqrt(var)) * open_ * rng.uniform(0.15, 0.8)
        out.append(candle(open_, max(open_, price) + spread, min(open_, price) - spread,
                          price, start_ts + i * HOUR))
    return out


def raises(call, error=ValueError):
    try:
        call()
    except error:
        return True
    return False


def close(a, b, tol=1e-9):
    return abs(a - b) < tol


# ---------------- helpers ----------------

def test_ewma_constant_and_halflife():
    assert all(close(v, 5.0) for v in ewma([5.0] * 20, 24))
    step = ewma([0.0] + [1.0] * 48, 24)
    assert close(step[24], 0.5)
    assert raises(lambda: ewma([1.0], 0))


def test_time_features_are_periodic():
    a = time_features(3 * HOUR)
    b = time_features(3 * HOUR + 86_400_000)
    assert all(close(x, y, 1e-9) for x, y in zip(a, b))
    assert close(a[0] ** 2 + a[1] ** 2, 1.0)


# ---------------- table ----------------

def test_table_rows_match_a_manual_calculation():
    candles = walk(900, seed=1)
    table = build_table([candles], horizon=12)
    ranges = [math.log(c.high / c.low) for c in candles]

    assert len(table) == 900 - 167 - 12

    for row in (0, len(table) // 2, len(table) - 1):
        index = table.timestamps[row] // HOUR
        assert close(table.y[row], math.log(sum(ranges[index + 1:index + 13]) / 12))
        assert close(table.columns["vol_fast"][row], math.log(sum(ranges[index - 23:index + 1]) / 24))
        assert close(table.columns["vol_slow"][row], math.log(sum(ranges[index - 167:index + 1]) / 168))
        assert close(table.naive["persistence"][row], table.columns["vol_fast"][row])


def test_table_never_crosses_a_gap():
    first = walk(600, seed=2, start_ts=0)
    second = walk(600, seed=3, start_ts=10**12)
    together = build_table([first, second], horizon=12)
    one = build_table([first], horizon=12)
    two = build_table([second], horizon=12)
    assert len(together) == len(one) + len(two)
    assert together.y == one.y + two.y


# ---------------- forecaster ----------------

def test_constructor_validation():
    assert raises(lambda: VolatilityForecaster(0))
    assert raises(lambda: VolatilityForecaster(HOUR, upper_quantile=0.4))
    assert raises(lambda: VolatilityForecaster(HOUR, fast=50, slow=10))
    assert raises(lambda: VolatilityForecaster(HOUR, horizon=0))


def test_unfitted_forecaster_refuses():
    model = VolatilityForecaster(HOUR)
    assert not model.is_fitted
    assert raises(lambda: model.forecast(walk(300, 4)), VolatilityError)


def test_fit_rows_needs_enough_rows():
    table = build_table([walk(400, seed=5)], horizon=12)
    model = VolatilityForecaster(HOUR, horizon=12)
    assert raises(lambda: model.fit_rows(
        {k: v[:100] for k, v in table.columns.items()}, table.y[:100]), VolatilityError)


def test_fit_recovers_a_planted_relation():
    rng = random.Random(6)
    n = 3000
    columns = {name: [rng.gauss(0, 1) for _ in range(n)] for name in BASE_FEATURES}
    y = [1.0 + 0.7 * a - 0.2 * b + rng.gauss(0, 0.05)
         for a, b in zip(columns["vol_fast"], columns["vol_slow"])]
    model = VolatilityForecaster(HOUR).fit_rows(columns, y)
    assert abs(model.coefficients[0] - 1.0) < 0.02
    assert abs(model.coefficients[1] - 0.7) < 0.02
    assert abs(model.coefficients[2] + 0.2) < 0.02
    assert model.smearing >= 1.0


def test_live_forecast_matches_the_table_path():
    candles = walk(5000, seed=7)
    table = build_table([candles], horizon=12)
    model = VolatilityForecaster(HOUR, horizon=12).fit([candles])
    predicted = model.predict_log_rows(table.columns)

    for k in (1000, 2500, 4000):
        live = model.forecast(candles[:k + 1])
        row = table.timestamps.index(candles[k].timestamp)
        assert close(live.log_expected, predicted[row], 1e-9)


def test_forecast_ignores_everything_before_the_window_and_after_the_end():
    candles = walk(4000, seed=8)
    model = VolatilityForecaster(HOUR, horizon=12).fit([candles])
    a = model.forecast(candles[:2000])
    b = model.forecast(candles[1000:2000])
    assert close(a.log_expected, b.log_expected, 1e-12)


def test_forecast_refuses_gaps_and_short_history():
    candles = walk(1000, seed=9)
    model = VolatilityForecaster(HOUR, horizon=12).fit([candles])
    assert raises(lambda: model.forecast(candles[:100]), VolatilityError)

    gapped = list(candles[:650]) + list(candles[660:700])
    assert raises(lambda: model.forecast(gapped), VolatilityError)

    old_gap = list(candles[:100]) + list(candles[110:600])
    assert model.forecast(old_gap).expected_range > 0


def test_upper_bound_holds_about_the_requested_share_in_sample():
    candles = walk(8000, seed=10)
    table = build_table([candles], horizon=12)
    model = VolatilityForecaster(HOUR, horizon=12, upper_quantile=0.9).fit([candles])
    predicted = model.predict_log_rows(table.columns)
    held = sum(1 for p, v in zip(predicted, table.y) if v <= p + model.upper_shift) / len(table)
    assert abs(held - 0.9) < 0.01


def test_forecast_values_are_positive_and_ordered():
    candles = walk(3000, seed=11)
    model = VolatilityForecaster(HOUR, horizon=12).fit([candles])
    f = model.forecast(candles)
    assert f.expected_range > 0 and f.upper_range > 0
    assert f.upper_range > f.expected_range * 0.9


# ---------------- walk-forward ----------------

def make_table(seed=12, n=4000, horizon=12):
    return build_table([walk(n, seed=seed)], horizon=horizon)


def test_walk_forward_covers_every_row_after_the_first_window():
    table = make_table()
    result = walk_forward(table, HOUR, horizon=12, min_train_rows=1500, refit_rows=500)
    assert len(result) == len(table) - 1500
    assert result.timestamps == table.timestamps[1500:]
    assert result.y == table.y[1500:]
    assert result.folds == math.ceil((len(table) - 1500) / 500)


def test_walk_forward_never_uses_purged_or_future_targets():
    table = make_table()
    base = walk_forward(table, HOUR, horizon=12, min_train_rows=1500, refit_rows=500)

    # rows from (start - horizon) on are not allowed to influence fold 1
    changed = list(table.y)
    for i in range(1500 - 12, len(changed)):
        changed[i] += 5.0
    other = VolatilityTable(changed, table.columns, table.naive, table.timestamps)
    shifted = walk_forward(other, HOUR, horizon=12, min_train_rows=1500, refit_rows=500)

    assert shifted.pred[:500] == base.pred[:500]
    assert shifted.pred[500:] != base.pred[500:]


def test_walk_forward_naive_is_bias_corrected():
    table = make_table()
    biased = VolatilityTable(
        table.y, table.columns,
        {"persistence": [v - 0.3 for v in table.y], "ewma": [v + 0.5 for v in table.y]},
        table.timestamps,
    )
    result = walk_forward(biased, HOUR, horizon=12, min_train_rows=1500, refit_rows=500)
    for series in result.naive.values():
        assert mse(result.y, series) < 1e-18


def test_walk_forward_validation():
    table = make_table()
    assert raises(lambda: walk_forward(table, HOUR, 12, min_train_rows=100, refit_rows=50))
    assert raises(lambda: walk_forward(table, HOUR, 12, min_train_rows=10**6, refit_rows=50))
    assert raises(lambda: walk_forward(table, HOUR, 12, min_train_rows=1500, refit_rows=0))


# ---------------- metrics ----------------

def test_mse():
    assert close(mse([1, 2, 3], [1, 2, 5]), 4 / 3)
    assert raises(lambda: mse([], []))
    assert raises(lambda: mse([1], [1, 2]))


def test_calibration_slope():
    p = [float(i) for i in range(50)]
    assert close(calibration_slope(p, [2.0 * v + 1 for v in p]), 2.0)
    assert close(calibration_slope(p, [0.5 * v for v in p]), 0.5)
    assert raises(lambda: calibration_slope([1.0] * 5, [1.0, 2.0, 3.0, 4.0, 5.0]))
    assert raises(lambda: calibration_slope([1.0, 2.0], [1.0, 2.0]))


def test_decile_table_orders_by_prediction():
    p = [math.log(i + 1) for i in range(100)]
    y = [math.log(2.0 * (i + 1)) for i in range(100)]
    table = decile_table(p, y)
    assert len(table) == 10
    assert all(close(a * 2.0, b, 1e-9) for a, b in table)
    assert rising_steps([b for _, b in table]) == 9
    assert raises(lambda: decile_table([1.0] * 5, [1.0] * 5))


def test_rising_steps():
    assert rising_steps([1, 2, 3]) == 2
    assert rising_steps([3, 2, 3, 1]) == 1
    assert rising_steps([1]) == 0


def test_coverage():
    assert close(coverage([1, 2, 3, 4], [1, 2, 2, 2]), 0.5)
    assert raises(lambda: coverage([], []))


def test_yearly_comparison_skips_short_years_and_picks_best_reference():
    year = 365 * 24 * 3_600_000
    base = 1_700_000_000_000
    stamps = [base + i * 1000 for i in range(2500)] + [base + year + i * 1000 for i in range(100)]
    n = len(stamps)
    y = [0.0] * n
    model = [0.1] * n
    good_ref = [0.2] * n
    bad_ref = [5.0] * n
    out = yearly_comparison(stamps, y, model, [bad_ref, good_ref])
    assert len(out) == 1
    (m, b), = out.values()
    assert close(m, 0.01) and close(b, 0.04)
