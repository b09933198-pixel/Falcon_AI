"""
Tests for the adverse-excursion quantiles and their walk-forward evaluation.

Hand-made candles test the DEFINITION of E; seeded synthetic series test
causality and the plumbing. They say nothing about any real market.
"""

import math
import random

from src.analysis.volatility import build_table
from src.analysis.volatility.excursion import (
    ExcursionModel,
    RISK_LEVELS,
    excursion_targets,
    ratio_quantiles,
    risk_level,
    trailing_ranks,
)
from src.analysis.volatility.forecaster import VolatilityError
from src.domain.models import Candle
from src.validation.excursion_walkforward import (
    baseline_quantiles,
    coverage_at,
    group_rows,
    level_index,
    median,
    pinball_loss,
    walk_forward_excursion,
)

HOUR = 3_600_000


def mk(ts, o, h, l, c):
    return Candle(
        timestamp=ts, open=o, high=h, low=l, close=c,
        volume=10.0, quote_volume=10.0 * c, trades=1, buy_volume=5.0, buy_quote_volume=5.0 * c,
    )


def synthetic(n, seed, start=0, gap=None):
    """Random walk with clustered volatility (two regimes that persist)."""

    rng = random.Random(seed)
    price = 1000.0
    sigma = 0.004
    out = []
    for i in range(n):
        if i % 400 == 0:
            sigma = rng.choice([0.002, 0.004, 0.008])
        if gap and gap[0] <= i < gap[1]:
            continue
        o = price
        price = o * math.exp(rng.gauss(0, sigma))
        hi = max(o, price) * (1 + abs(rng.gauss(0, sigma)) * 0.5)
        lo = min(o, price) * (1 - abs(rng.gauss(0, sigma)) * 0.5)
        out.append(mk(start + i * HOUR, o, hi, lo, price))
    return out


def raises(call, error=ValueError):
    try:
        call()
    except error:
        return True
    return False


def close(a, b, tol=1e-9):
    return abs(a - b) < tol


# ---------------- definition of E ----------------

def test_excursion_is_the_larger_side_from_the_next_open():
    """Needs fast=2, slow=2, horizon=2 so every early row exists; rows start at index 1."""

    candles = [
        mk(0, 100, 101, 99, 100),
        mk(1 * HOUR, 100, 101, 99, 100),
        mk(2 * HOUR, 100, 104, 99, 103),     # next open 100 (row at index 1)
        mk(3 * HOUR, 103, 105, 98, 99),
        mk(4 * HOUR, 99, 100, 97, 98),
    ]
    e = excursion_targets([candles], horizon=2, fast=2, slow=2)
    # row i=1: entry open[2]=100, window candles 2..3: high 105, low 98 -> up 5, down 2 -> 5/100
    # row i=2: entry open[3]=103, window candles 3..4: high 105, low 97 -> up 2, down 6 -> 6/103
    assert len(e) == 2
    assert close(e[0], 0.05) and close(e[1], 6 / 103)


def test_excursion_rows_align_with_the_volatility_table_and_skip_gaps():
    candles_a = synthetic(900, seed=1)
    candles_b = synthetic(700, seed=2, start=2000 * HOUR)
    segments = [candles_a, candles_b]
    table = build_table(segments, horizon=24)
    e = excursion_targets(segments, horizon=24)
    assert len(e) == len(table)
    assert all(v > 0 for v in e)


# ---------------- ratio quantiles ----------------

def test_ratio_quantiles_are_empirical_and_need_enough_rows():
    expected = [0.01] * 1000
    excursions = [0.01 * (1 + k / 1000) for k in range(1000)]
    q50, q95 = ratio_quantiles(excursions, expected, (0.5, 0.95))
    assert abs(q50 - 1.5) < 0.01 and abs(q95 - 1.95) < 0.01
    assert raises(lambda: ratio_quantiles([0.01] * 10, [0.01] * 10), VolatilityError)
    assert raises(lambda: ratio_quantiles([0.01] * 300, [0.01] * 299), VolatilityError)


# ---------------- trailing ranks / risk level ----------------

def test_trailing_ranks_basics_and_ties():
    out = trailing_ranks(list(range(30)), window=30, min_valid=10)
    assert out[:9] == [None] * 9
    assert all(close(v, (i + 0.5) / (i + 1)) for i, v in enumerate(out) if i >= 9)

    flat = trailing_ranks([5.0] * 40, window=30, min_valid=10)
    assert all(close(v, 0.5) for v in flat[9:])


def test_trailing_ranks_window_eviction_missing_values_and_validation():
    values = [float(i) for i in range(60)]
    out = trailing_ranks(values, window=10, min_valid=5)
    assert all(v > 0.9 for v in out[5:])

    gaps = [None if i % 3 == 0 else float(i) for i in range(60)]
    out = trailing_ranks(gaps, window=30, min_valid=5)
    assert all(out[i] is None for i in range(0, 60, 3))

    assert raises(lambda: trailing_ranks([1.0], window=1))
    assert raises(lambda: trailing_ranks([1.0], window=10, min_valid=20))


def test_trailing_ranks_have_no_lookahead():
    rng = random.Random(3)
    values = [rng.gauss(0, 1) for _ in range(400)]
    full = trailing_ranks(values, 100, 30)
    for n in (120, 301, 399):
        assert trailing_ranks(values[:n], 100, 30) == full[:n]


def test_risk_level_boundaries():
    assert [risk_level(r) for r in (0.0, 0.2499, 0.25, 0.7499, 0.75, 0.9499, 0.95, 1.0)] == [
        "low", "low", "normal", "normal", "high", "high", "extreme", "extreme",
    ]
    assert RISK_LEVELS == ("low", "normal", "high", "extreme")
    assert raises(lambda: risk_level(1.2))
    assert [level_index(r) for r in (0.1, 0.5, 0.9, 0.97)] == [0, 1, 2, 3]


# ---------------- model ----------------

def test_model_quantiles_are_ordered_and_refuse_bad_input():
    candles = synthetic(9000, seed=4)
    table = build_table([candles], horizon=24)
    e = excursion_targets([candles], horizon=24)
    model = ExcursionModel(HOUR, 24).fit_rows(table.columns, table.y, e)

    sheet = model.forecast(candles[:6000])
    q = sheet.quantiles
    assert 0 < sheet.expected_range and 0 < q[0.5] < q[0.8] < q[0.95]
    assert sheet.upper_range > sheet.expected_range

    assert raises(lambda: ExcursionModel(HOUR).forecast(candles[:6000]), VolatilityError)
    assert raises(lambda: model.forecast(candles[:100]), VolatilityError)
    gapped = candles[:6000]
    gapped = gapped[:-50] + [mk(c.timestamp + HOUR, c.open, c.high, c.low, c.close) for c in gapped[-50:]]
    assert raises(lambda: model.forecast(gapped), VolatilityError)


# ---------------- metrics ----------------

def test_metrics():
    assert coverage_at([1, 2, 3, 4], [2, 2, 2, 5]) == 0.75
    assert close(pinball_loss([1.0, 3.0], [2.0, 2.0], 0.8), (0.2 * 1.0 + 0.8 * 1.0) / 2)
    assert pinball_loss([2.0], [2.0], 0.9) == 0.0
    assert median([3, 1, 2]) == 2 and median([1, 2, 3, 4]) == 2.5
    assert group_rows([0, 1, 0, 2]) == {0: [0, 2], 1: [1], 2: [3]}
    assert raises(lambda: coverage_at([], []))
    assert raises(lambda: pinball_loss([1.0], [1.0, 2.0], 0.5))


# ---------------- baseline B ----------------

def test_baseline_uses_only_outcomes_known_at_decision_time():
    n = 5000
    stamps = [i * HOUR for i in range(n)]
    base = [0.01 + 0.001 * math.sin(i / 50) for i in range(n)]
    a = baseline_quantiles(stamps, base, 3000, 24 * HOUR, (0.8,), 2000, min_rows=500)

    changed = list(base)
    for i in range(3500, n):              # outcomes that only become known after row 3500
        changed[i] = 5.0
    b = baseline_quantiles(stamps, changed, 3000, 24 * HOUR, (0.8,), 2000, min_rows=500)

    # decisions up to row 3500 + 24 cannot know those outcomes yet
    assert a[0.8][:500 + 24] == b[0.8][:500 + 24]
    assert a[0.8][-1] != b[0.8][-1]
    assert raises(lambda: baseline_quantiles(stamps, base, 100, 24 * HOUR, (0.8,), 2000, min_rows=500))


# ---------------- walk-forward ----------------

def test_walk_forward_is_calibrated_on_synthetic_data_and_has_no_lookahead():
    candles = synthetic(9000, seed=5)
    table = build_table([candles], horizon=24)
    e = excursion_targets([candles], horizon=24)

    result = walk_forward_excursion(
        table, e, HOUR, horizon=24, min_train_rows=3000, refit_rows=500, rank_window=1500,
    )

    assert result.folds >= 5 and len(result) == len(table) - 3000
    for q, target in ((0.5, 0.5), (0.8, 0.8), (0.95, 0.95)):
        assert abs(coverage_at(result.excursion, result.quantiles[q]) - target) < 0.06

    medians = [
        median([result.excursion[i] for i in rows])
        for _, rows in sorted(group_rows([level_index(r) for r in result.ranks]).items())
    ]
    assert len(medians) == 4 and medians[-1] > medians[0]

    # no lookahead: outcomes of the last 2500 rows must not change any forecast for the first rows
    changed = list(e)
    for i in range(len(e) - 2500, len(e)):
        changed[i] = 9.0
    other = walk_forward_excursion(
        table, changed, HOUR, horizon=24, min_train_rows=3000, refit_rows=500, rank_window=1500,
    )
    k = 1500
    assert other.expected[:k] == result.expected[:k]
    assert other.quantiles[0.95][:k] == result.quantiles[0.95][:k]
    assert other.ranks == result.ranks


def test_walk_forward_validates_input():
    candles = synthetic(3500, seed=6)
    table = build_table([candles], horizon=24)
    e = excursion_targets([candles], horizon=24)
    assert raises(lambda: walk_forward_excursion(table, e[:-1], HOUR, min_train_rows=3000))
    assert raises(lambda: walk_forward_excursion(table, e, HOUR, min_train_rows=100))
    assert raises(lambda: walk_forward_excursion(table, e, HOUR, min_train_rows=10_000))
