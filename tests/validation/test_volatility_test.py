"""
Tests for the volatility forecast test.

Hand-made numbers and seeded synthetic series test the MACHINERY (window
alignment, gap safety, no lookahead, least squares, statistics). They say
nothing about any real market.
"""

import math
import random

from src.domain.models import Candle
from src.validation.volatility_test import (
    BASE_NAMES,
    Dataset,
    analyze_feature,
    baseline_report,
    build_dataset,
    correlation_by_year,
    future_mean,
    log_ranges,
    ols_fit,
    ols_predict,
    out_of_sample_r2,
    past_mean,
    r_squared,
    residual_shift_test,
    residuals,
    structure_features,
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
    out = []
    for i in range(n):
        open_ = price
        price = open_ * (1.0 + rng.gauss(0.0, vol))
        spread = open_ * rng.uniform(0.0005, 0.003)
        out.append(candle(open_, max(open_, price) + spread, min(open_, price) - spread,
                          price, start_ts + i * HOUR))
    return out


def close(a, b, tol=1e-9):
    return abs(a - b) < tol


# ---------------- windows ----------------

def test_log_ranges():
    out = log_ranges([candle(100, 110, 100, 105)])
    assert close(out[0], math.log(1.1))


def test_past_mean_alignment():
    out = past_mean([1, 2, 3, 4, 5, 6], 3)
    assert out[:2] == [None, None]
    assert [round(v, 9) for v in out[2:]] == [2.0, 3.0, 4.0, 5.0]


def test_future_mean_alignment():
    out = future_mean([1, 2, 3, 4, 5, 6], 2)
    assert [round(v, 9) for v in out[:4]] == [2.5, 3.5, 4.5, 5.5]
    assert out[4] is None and out[5] is None


def test_future_mean_short_series_is_all_none():
    assert future_mean([1, 2], 2) == [None, None]
    assert future_mean([1, 2, 3], 2) == [2.5, None, None]


def test_window_arguments_are_validated():
    for call in (lambda: past_mean([1, 2], 0), lambda: future_mean([1, 2], 0),
                 lambda: past_mean([1, 2], 1.5), lambda: future_mean([1, 2], "2")):
        try:
            call()
        except ValueError:
            continue
        raise AssertionError("expected ValueError")


# ---------------- least squares ----------------

def test_ols_recovers_exact_coefficients():
    rng = random.Random(1)
    x1 = [rng.gauss(0, 1) for _ in range(500)]
    x2 = [rng.gauss(0, 2) + 0.3 * a for a in x1]
    y = [2.0 + 3.0 * a - 1.5 * b for a, b in zip(x1, x2)]
    fit = ols_fit([x1, x2], y)
    assert close(fit[0], 2.0) and close(fit[1], 3.0) and close(fit[2], -1.5)
    assert close(r_squared(y, ols_predict(fit, [x1, x2])), 1.0)


def test_ols_with_noise_is_close():
    rng = random.Random(2)
    x = [rng.gauss(0, 1) for _ in range(5000)]
    y = [1.0 + 0.5 * a + rng.gauss(0, 0.3) for a in x]
    fit = ols_fit([x], y)
    assert abs(fit[1] - 0.5) < 0.03 and abs(fit[0] - 1.0) < 0.03


def test_collinear_regressors_are_rejected():
    x = [float(i) for i in range(50)]
    y = [2.0 * v for v in x]
    try:
        ols_fit([x, [2.0 * v for v in x]], y)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_ols_input_validation():
    for call in (lambda: ols_fit([], [1.0, 2.0, 3.0]),
                 lambda: ols_fit([[1.0, 2.0]], [1.0, 2.0, 3.0]),
                 lambda: ols_fit([[1.0, 2.0]], [1.0, 2.0])):
        try:
            call()
        except ValueError:
            continue
        raise AssertionError("expected ValueError")


def test_r_squared_perfect_and_mean_model():
    y = [1.0, 2.0, 3.0, 4.0]
    assert close(r_squared(y, y), 1.0)
    assert close(r_squared(y, [2.5] * 4), 0.0)
    assert r_squared(y, [10.0] * 4) < 0


def test_residuals_are_orthogonal_to_regressors():
    rng = random.Random(3)
    x1 = [rng.gauss(0, 1) for _ in range(800)]
    x2 = [rng.gauss(0, 1) for _ in range(800)]
    y = [a - b + rng.gauss(0, 1) for a, b in zip(x1, x2)]
    res = residuals([x1, x2], y)
    assert abs(sum(res)) < 1e-6
    assert abs(sum(r * a for r, a in zip(res, x1))) < 1e-6
    assert abs(sum(r * b for r, b in zip(res, x2))) < 1e-6


# ---------------- statistics ----------------

def blocks(n, rng, size=100):
    out = []
    value = 0.0
    for i in range(n):
        if i % size == 0:
            value = rng.gauss(0, 1)
        out.append(value)
    return out


def test_shift_test_detects_a_planted_relation():
    rng = random.Random(4)
    a = blocks(8000, rng)
    b = [0.6 * x + rng.gauss(0, 1) for x in a]
    corr, p = residual_shift_test(a, b, shifts=300)
    assert corr > 0.2
    assert p < 0.02


def test_shift_test_does_not_invent_relations_in_noise():
    significant = 0
    for seed in range(20):
        rng = random.Random(500 + seed)
        a = blocks(6000, rng)
        b = blocks(6000, rng)
        _, p = residual_shift_test(a, b, shifts=200, seed=seed)
        if p < 0.05:
            significant += 1
    assert significant <= 6


def test_shift_test_validates_inputs():
    for call in (lambda: residual_shift_test([1.0] * 30, [1.0] * 29),
                 lambda: residual_shift_test([1.0] * 10, [1.0] * 10),
                 lambda: residual_shift_test([0.0] * 100, [1.0] * 100)):
        try:
            call()
        except ValueError:
            continue
        raise AssertionError("expected ValueError")


def test_correlation_by_year_skips_short_years():
    year = 365 * 24 * 3_600_000
    stamps = [1_700_000_000_000 + i * 1000 for i in range(600)]
    stamps += [1_700_000_000_000 + year + i * 1000 for i in range(50)]
    a = [float(i % 7) for i in range(650)]
    b = list(a)
    out = correlation_by_year(stamps, a, b)
    years = sorted(out)
    assert abs(out[years[0]] - 1.0) < 1e-9
    assert out[years[1]] is None


def test_out_of_sample_gain_for_planted_and_noise_features():
    rng = random.Random(6)
    n = 4000
    base = [[rng.gauss(0, 1) for _ in range(n)] for _ in range(2)]
    planted = [rng.gauss(0, 1) for _ in range(n)]
    noise = [rng.gauss(0, 1) for _ in range(n)]
    y = [a + b + 0.5 * p + rng.gauss(0, 1) for a, b, p in zip(base[0], base[1], planted)]
    base_r2, with_planted = out_of_sample_r2(base, [planted], y)
    _, with_noise = out_of_sample_r2(base, [noise], y)
    assert with_planted - base_r2 > 0.03
    assert with_noise - base_r2 < 0.005


def test_out_of_sample_needs_enough_samples():
    try:
        out_of_sample_r2([[1.0] * 12], [[1.0] * 12], [1.0] * 12)
    except ValueError:
        return
    raise AssertionError("expected ValueError")


# ---------------- features and dataset ----------------

def test_structure_features_have_no_lookahead():
    candles = walk(500, seed=7)
    for strength in (2, 5):
        full = structure_features(candles, strength)
        for n in (60, 150, 333, 499):
            prefix = structure_features(candles[:n], strength)
            for name in ("leg", "age", "ranging"):
                assert getattr(prefix, name)[n - 1] == getattr(full, name)[n - 1], (strength, n, name)


def test_features_are_none_before_the_first_swings():
    feats = structure_features(walk(200, seed=8), 5)
    assert feats.leg[0] is None and feats.age[0] is None and feats.ranging[0] is None
    assert feats.leg[-1] is not None and feats.age[-1] is not None


def test_dataset_rows_match_a_manual_calculation():
    candles = walk(900, seed=9)
    data = build_dataset([candles], strength=3, horizon=12, fast=24, slow=168)
    assert len(data) > 300

    ranges = log_ranges(candles)
    for row in (0, len(data) // 2, len(data) - 1):
        index = data.timestamps[row] // HOUR
        expected_y = math.log(sum(ranges[index + 1:index + 13]) / 12)
        expected_fast = math.log(sum(ranges[index - 23:index + 1]) / 24)
        expected_slow = math.log(sum(ranges[index - 167:index + 1]) / 168)
        assert close(data.y[row], expected_y, 1e-9)
        assert close(data.columns["vol_fast"][row], expected_fast, 1e-9)
        assert close(data.columns["vol_slow"][row], expected_slow, 1e-9)
        angle = 2 * math.pi * (data.timestamps[row] % 86_400_000) / 86_400_000
        assert close(data.columns["sin1"][row], math.sin(angle), 1e-9)


def test_dataset_never_crosses_a_gap():
    first = walk(700, seed=10, start_ts=0)
    second = walk(700, seed=11, start_ts=10**12)
    together = build_dataset([first, second], strength=3, horizon=12)
    alone_first = build_dataset([first], strength=3, horizon=12)
    alone_second = build_dataset([second], strength=3, horizon=12)
    assert len(together) == len(alone_first) + len(alone_second)
    assert together.y[:len(alone_first)] == alone_first.y
    assert together.y[len(alone_first):] == alone_second.y


def test_features_cache_gives_identical_datasets():
    segments = [walk(600, seed=12)]
    cache = {}
    a = build_dataset(segments, 3, 12, features_cache=cache)
    b = build_dataset(segments, 3, 12, features_cache=cache)
    assert a.y == b.y and a.columns == b.columns


# ---------------- end to end ----------------

def test_analyze_feature_detects_a_planted_feature_and_ignores_noise():
    segments = [walk(6000, seed=13)]
    data = build_dataset(segments, 3, 12)
    base = [data.columns[name] for name in BASE_NAMES]
    ry = residuals(base, data.y)

    rng = random.Random(14)
    planted = dict(data.columns)
    planted["leg"] = [r + rng.gauss(0, 2 * (sum(x * x for x in ry) / len(ry)) ** 0.5) for r in ry]
    noisy = dict(data.columns)
    noisy["leg"] = [rng.gauss(0, 1) for _ in ry]

    good = analyze_feature(Dataset(data.y, planted, data.timestamps), "leg", shifts=200)
    bad = analyze_feature(Dataset(data.y, noisy, data.timestamps), "leg", shifts=200)

    assert good.correlation > 0.1 and good.p_value < 0.01
    assert bad.p_value > 0.01
    assert good.oos_gain > bad.oos_gain


def test_constant_feature_gives_p_one():
    segments = [walk(1500, seed=15)]
    data = build_dataset(segments, 3, 12)
    columns = dict(data.columns)
    columns["age"] = [1.0] * len(data)
    result = analyze_feature(Dataset(data.y, columns, data.timestamps), "age", shifts=50)
    assert result.p_value == 1.0 and result.correlation != result.correlation


def test_baseline_report_returns_two_numbers():
    data = build_dataset([walk(3000, seed=16)], 3, 12)
    in_sample, out_sample = baseline_report(data)
    assert -1.0 < in_sample < 1.0 and -1.0 < out_sample < 1.0
