"""
Tests for the price-action signal scan.

Hand-made candles test the DEFINITIONS (what counts as a sweep, a compression,
a resampled bar); seeded synthetic series test causality and the statistics.
They say nothing about any real market.
"""

import math
import random

from src.domain.models import Candle
from src.validation.signal_scan import (
    Events,
    block_sign_flip_test,
    breakout_signals,
    collect_events,
    evaluate_events,
    forward_returns_bp,
    hour_signals,
    pullback_signals,
    resample,
    sweep_signals,
)

HOUR = 3_600_000
DAY = 86_400_000


def candle(open_, high, low, close, ts=0):
    return Candle(
        timestamp=ts, open=open_, high=high, low=low, close=close,
        volume=1.0, quote_volume=2.0, trades=3, buy_volume=0.5, buy_quote_volume=1.0,
    )


def series(rows, start=0):
    return [candle(o, h, l, c, start + i * HOUR) for i, (o, h, l, c) in enumerate(rows)]


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


def raises(call, error=ValueError):
    try:
        call()
    except error:
        return True
    return False


def close(a, b, tol=1e-9):
    return abs(a - b) < tol


def mirror(candles, top=20.0):
    return [candle(top - c.open, top - c.low, top - c.high, top - c.close, c.timestamp) for c in candles]


# ---------------- forward returns ----------------

def test_forward_returns_bp():
    candles = series([(100, 101, 99, 100), (100, 102, 99, 101), (110, 112, 109, 111), (120, 121, 119, 120)])
    out = forward_returns_bp(candles, 2)
    assert close(out[0], (111 / 100 - 1) * 10_000)
    assert close(out[1], (120 / 110 - 1) * 10_000)
    assert out[2] is None and out[3] is None
    assert raises(lambda: forward_returns_bp(candles, 0))


# ---------------- resample ----------------

def aligned(n, factor=4, offset=0):
    base = 10 * factor * HOUR
    return [candle(100 + i, 101 + i, 99 + i, 100.5 + i, base + (i + offset) * HOUR) for i in range(n)]


def test_resample_aggregates_aligned_groups():
    candles = aligned(8)
    bars, last = resample(candles, 4, HOUR)
    assert len(bars) == 2 and last == [3, 7]
    first = bars[0]
    assert first.timestamp == candles[0].timestamp
    assert first.open == candles[0].open and first.close == candles[3].close
    assert first.high == max(c.high for c in candles[:4]) and first.low == min(c.low for c in candles[:4])
    assert first.volume == 4.0 and first.trades == 12


def test_resample_drops_misaligned_start_incomplete_tail_and_gaps():
    candles = aligned(11, offset=1)
    bars, last = resample(candles, 4, HOUR)
    assert [b.timestamp % (4 * HOUR) for b in bars] == [0, 0]
    assert last == [6, 10]

    gapped = aligned(8)
    del gapped[2]
    bars, _ = resample(gapped, 4, HOUR)
    assert len(bars) == 1


def test_resample_validation():
    assert raises(lambda: resample(aligned(8), 1, HOUR))
    assert raises(lambda: resample(aligned(8), 4, 0))


# ---------------- hour signals ----------------

def test_hour_signals():
    candles = walk(72, seed=1)
    out = hour_signals(candles, 5)
    assert [i for i, v in enumerate(out) if v] == [5, 29, 53]
    assert raises(lambda: hour_signals(candles, 24))


# ---------------- sweeps ----------------

SWEEP_ROWS = [
    (12, 13, 11, 12),
    (12, 12.5, 10, 11),
    (11, 11.5, 5, 6),      # swing low, confirmed after two more candles
    (6, 9, 6, 8),
    (8, 10, 7, 9),
    (9, 10, 8, 9),
    (9, 9.5, 4, 8),        # pokes below 5 and closes back above -> +1
    (8, 9, 3.5, 4.5),      # swing already used -> 0
    (4.5, 9, 4.4, 8),
    (8, 9, 7, 8),
    (8, 9, 7, 8),
]


def test_sweep_bull_signal_fires_once():
    out = sweep_signals(series(SWEEP_ROWS), 2)
    assert out[6] == 1
    assert sum(1 for v in out if v) == 1


def test_sweep_requires_close_back_inside_and_consumes_the_swing():
    rows = list(SWEEP_ROWS)
    rows[6] = (9, 9.5, 4, 4.5)          # closes below the swing -> a break, not a sweep
    rows[7] = (4.5, 9, 3.5, 8)          # later wick-and-close-back must not fire either
    out = sweep_signals(series(rows), 2)
    assert not any(out)


def test_sweep_bear_signal_is_the_mirror_image():
    out = sweep_signals(mirror(series(SWEEP_ROWS)), 2)
    assert out[6] == -1
    assert sum(1 for v in out if v) == 1


def test_sweep_ignores_swings_not_yet_confirmed():
    rows = [(12, 13, 11, 12), (12, 12.5, 10, 11), (11, 11.5, 5, 6), (6, 9, 4, 8)]
    assert not any(sweep_signals(series(rows), 2))


# ---------------- breakout ----------------

def compression_rows(tail):
    rows = []
    for i in range(40):
        rows.append((100, 101.0, 99.0, 100.5 if i % 2 else 99.5))
    for k in range(8):
        half = 0.05 - 0.004 * k
        rows.append((100, 100 + half, 100 - half, 100))
    return rows + tail


PARAMS = dict(lookback=5, vol_window=5, history=30, quantile=0.2)


def test_breakout_after_compression_up_and_down():
    up = series(compression_rows([(100, 103, 99.9, 102.5)]))
    out = breakout_signals(up, **PARAMS)
    assert out[-1] == 1 and sum(1 for v in out if v) == 1

    down = series(compression_rows([(100, 100.1, 97, 97.5)]))
    out = breakout_signals(down, **PARAMS)
    assert out[-1] == -1 and sum(1 for v in out if v) == 1


def test_breakout_without_compression_or_inside_the_range_is_ignored():
    rows = [(100, 101.0, 99.0, 100.5 if i % 2 else 99.5) for i in range(60)]
    rows.append((100, 103, 99.9, 102.5))
    assert not any(breakout_signals(series(rows), **PARAMS))

    inside = series(compression_rows([(100, 100.01, 99.99, 100.0)]))
    assert not any(breakout_signals(inside, **PARAMS))


def test_breakout_validation():
    assert raises(lambda: breakout_signals(walk(50, 1), lookback=0))
    assert raises(lambda: breakout_signals(walk(50, 1), quantile=1.5))


# ---------------- causality ----------------

def test_no_signal_uses_future_candles():
    candles = walk(1600, seed=2)
    makers = {
        "sweep": lambda c: sweep_signals(c, 3),
        "breakout": lambda c: breakout_signals(c, history=200),
        "pullback": lambda c: pullback_signals(c, HOUR),
        "hour": lambda c: hour_signals(c, 7),
    }

    for name, make in makers.items():
        full = make(candles)
        for n in (900, 1203, 1555):
            assert make(candles[:n]) == full[:n], (name, n)


def test_pullback_is_quiet_without_swings_and_uses_both_directions_on_noise():
    trend = series([(100 + i, 101 + i, 99 + i, 100.5 + i) for i in range(200)], start=0)
    assert not any(pullback_signals(trend, HOUR))

    out = pullback_signals(walk(6000, seed=3), HOUR)
    assert set(out) <= {-1, 0, 1}
    assert out.count(1) > 100 and out.count(-1) > 100


# ---------------- events ----------------

def test_collect_events_skips_incomplete_windows_and_gaps():
    first = walk(100, seed=4, start_ts=0)
    second = walk(100, seed=5, start_ts=10**12)
    events = collect_events([first, second], lambda seg: [1] * len(seg), horizon=10)
    assert len(events) == 2 * (100 - 10)
    assert raises(lambda: collect_events([first], lambda seg: [1], horizon=5))


def test_collect_events_signs_the_edge():
    candles = walk(60, seed=6)
    up = collect_events([candles], lambda seg: [1] * len(seg), horizon=5)
    down = collect_events([candles], lambda seg: [-1] * len(seg), horizon=5)
    assert all(close(a, -b) for a, b in zip(up.edges, down.edges))


# ---------------- statistics ----------------

def planted_events(n, seed, effect, years=4):
    rng = random.Random(seed)
    span = years * 365 * DAY
    base = 1_600_000_000_000
    stamps = sorted(base + int(rng.random() * span) for _ in range(n))
    edges = [effect + rng.gauss(0.0, 120.0) for _ in range(n)]
    return Events(stamps, edges)


def test_sign_flip_detects_an_effect_and_not_noise():
    real = planted_events(1500, 1, effect=15.0)
    p_real = evaluate_events(real, flips=1000).p_value
    assert p_real < 0.01

    hits = 0
    for seed in range(20):
        p = evaluate_events(planted_events(1500, 100 + seed, effect=0.0), flips=300, seed=seed).p_value
        if p < 0.05:
            hits += 1
    assert hits <= 4


def test_evaluate_events_reports_mean_hit_rate_and_years():
    result = evaluate_events(planted_events(2000, 2, effect=20.0), flips=300)
    assert 12 < result.mean_edge < 28
    assert 0.5 < result.hit_rate < 0.6
    assert result.years_usable >= 3 and result.years_same_sign >= result.years_usable - 1
    assert result.events == 2000


def test_statistics_validation():
    assert raises(lambda: block_sign_flip_test([1.0, 2.0], [1]))
    assert raises(lambda: block_sign_flip_test([1.0] * 5, [1, 2, 3, 4, 5]))
    assert raises(lambda: evaluate_events(Events([1] * 10, [1.0] * 10)))


def test_end_to_end_cheating_signal_is_caught_and_random_signal_is_not():
    candles = walk(8000, seed=7)
    returns = forward_returns_bp(candles, 12)

    def cheat(seg):
        return [0 if r is None else (1 if r > 0 else -1) for r in returns]

    rng = random.Random(8)
    noise = [rng.choice((-1, 0, 1)) for _ in candles]

    good = evaluate_events(collect_events([candles], cheat, 12), flips=500)
    bad = evaluate_events(collect_events([candles], lambda seg: noise, 12), flips=500)

    assert good.p_value < 0.01 and good.mean_edge > 20
    assert bad.p_value > 0.01
