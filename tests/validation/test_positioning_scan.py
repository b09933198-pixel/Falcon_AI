"""
Tests for the positioning / order-flow signal scan.

Hand-made rows test the DEFINITIONS and the availability rules (nothing is used
before it could have been known); seeded random data tests causality. They say
nothing about any real market.
"""

import math
import random

from src.domain.models import Candle
from src.validation.positioning_scan import (
    FIVE_MIN_MS,
    HOUR_MS,
    Positioning,
    funding_feature,
    gated_direction,
    open_interest_change_feature,
    past_return_sign,
    percentile_signals,
    ratio_feature,
    spot_taker_feature,
    split_events,
    taker_flow_feature,
)
from src.validation.signal_scan import Events

DAY = 86_400_000


def candle(ts, close=100.0, volume=10.0, buy=5.0):
    return Candle(
        timestamp=ts, open=close, high=close + 1, low=close - 1, close=close,
        volume=volume, quote_volume=volume * close, trades=1, buy_volume=buy, buy_quote_volume=buy * close,
    )


def candles_at(hours, start=0):
    return [candle(start + h * HOUR_MS) for h in hours]


def walk(n, seed):
    rng = random.Random(seed)
    price = 1000.0
    out = []
    for i in range(n):
        price *= 1.0 + rng.gauss(0.0, 0.004)
        volume = rng.uniform(5, 15)
        out.append(candle(i * HOUR_MS, price, volume, volume * rng.uniform(0.3, 0.7)))
    return out


def metric_rows(start, stop, step=FIVE_MIN_MS, oi=lambda ts: 1000.0, top=lambda ts: 1.5,
                count=lambda ts: 1.2, taker=lambda ts: 1.0):
    return [(ts, oi(ts), oi(ts) * 10, 1.0, top(ts), count(ts), taker(ts)) for ts in range(start, stop, step)]


def raises(call, error=ValueError):
    try:
        call()
    except error:
        return True
    return False


def close(a, b, tol=1e-9):
    return abs(a - b) < tol


# ---------------- container ----------------

def test_from_rows_sorts_and_maps_columns():
    pos = Positioning.from_rows(
        [(2000, 8, 0.2), (1000, 8, 0.1)],
        [(600_000, 5.0, 50.0, 1.0, 2.0, 3.0, 4.0), (300_000, 6.0, 60.0, 1.1, 2.1, 3.1, 4.1)],
    )
    assert pos.funding_ts == [1000, 2000] and pos.funding_rate == [0.1, 0.2]
    assert pos.metric_ts == [300_000, 600_000]
    assert pos.open_interest == [6.0, 5.0] and pos.top_ls == [2.1, 2.0]
    assert pos.count_ls == [3.1, 3.0] and pos.taker_ls == [4.1, 4.0]


# ---------------- funding ----------------

def test_funding_feature_is_known_only_from_its_calc_time():
    pos = Positioning.from_rows([(0, 8, 0.1), (8 * HOUR_MS, 8, 0.2)], [])
    out = funding_feature(candles_at([0, 6, 7, 8, 19, 20]), pos)
    # candle opening at h closes at h+1
    assert out[0] == 0.1 and out[1] == 0.1
    assert out[2] == 0.2          # closes exactly at the second funding time
    assert out[3] == 0.2
    assert out[4] is None         # closes at 20h, 12h after the funding at 8h: too old
    assert out[5] is None


def test_funding_feature_staleness_limit():
    pos = Positioning.from_rows([(0, 8, 0.1)], [])
    assert funding_feature(candles_at([7]), pos)[0] == 0.1
    assert funding_feature(candles_at([9]), pos)[0] is None
    assert funding_feature(candles_at([0]), Positioning.from_rows([], []))[0] is None


# ---------------- open interest ----------------

def growth(ts):
    return 1000.0 * math.exp(0.1 * ts / DAY)


def test_open_interest_change_matches_a_manual_value():
    pos = Positioning.from_rows([], metric_rows(0, 5 * DAY, oi=growth))
    out = open_interest_change_feature(candles_at(range(30, 50)), pos)
    assert all(close(v, 0.1, 1e-9) for v in out)
    assert open_interest_change_feature(candles_at([5]), pos)[0] is None


def test_metrics_row_is_usable_only_five_minutes_after_its_stamp():
    t = 48 * HOUR_MS + HOUR_MS
    base = metric_rows(0, t - FIVE_MIN_MS, oi=growth)
    exact = base + [(t - FIVE_MIN_MS, 5000.0, 0, 1.0, 1.5, 1.2, 1.0)]
    late = base + [(t - FIVE_MIN_MS + 1, 9000.0, 0, 1.0, 1.5, 1.2, 1.0)]
    target = [candle(48 * HOUR_MS)]

    with_exact = open_interest_change_feature(target, Positioning.from_rows([], exact))[0]
    without_late = open_interest_change_feature(target, Positioning.from_rows([], late))[0]
    plain = open_interest_change_feature(target, Positioning.from_rows([], base))[0]

    assert with_exact is not None and abs(with_exact - plain) > 0.1
    assert close(without_late, plain)


def test_open_interest_feature_refuses_stale_rows():
    rows = metric_rows(0, 40 * HOUR_MS, oi=growth) + metric_rows(60 * HOUR_MS, 80 * HOUR_MS, oi=growth)
    pos = Positioning.from_rows([], rows)
    assert open_interest_change_feature(candles_at([45]), pos)[0] is None


# ---------------- taker flow ----------------

def test_taker_flow_mean_and_requirements():
    rows = metric_rows(0, 10 * HOUR_MS, taker=lambda ts: math.e)
    pos = Positioning.from_rows([], rows)
    out = taker_flow_feature(candles_at([6, 7]), pos)
    assert all(close(v, 1.0) for v in out)
    assert taker_flow_feature(candles_at([1]), pos)[0] is None

    sparse = Positioning.from_rows([], metric_rows(0, 10 * HOUR_MS, step=3 * FIVE_MIN_MS, taker=lambda ts: math.e))
    assert taker_flow_feature(candles_at([6]), sparse)[0] is None


def test_taker_flow_ignores_future_rows_and_bad_values():
    rows = metric_rows(0, 10 * HOUR_MS, taker=lambda ts: math.e)
    t = 7 * HOUR_MS
    spoiled = [(ts, a, b, c, d, e, (50.0 if ts > t - FIVE_MIN_MS else f)) for ts, a, b, c, d, e, f in rows]
    spoiled = [r if r[0] % (7 * FIVE_MIN_MS) else r[:6] + (-1.0,) for r in spoiled]
    pos = Positioning.from_rows([], spoiled)
    out = taker_flow_feature([candle(6 * HOUR_MS)], pos)[0]
    assert close(out, 1.0)


# ---------------- ratios ----------------

def test_ratio_feature_uses_the_newest_usable_row():
    rows = metric_rows(0, 5 * HOUR_MS, count=lambda ts: 1.0 + ts / (5 * HOUR_MS))
    pos = Positioning.from_rows([], rows)
    out = ratio_feature([candle(2 * HOUR_MS)], pos, "count_ls")[0]
    last = 3 * HOUR_MS - FIVE_MIN_MS
    assert close(out, math.log(1.0 + last / (5 * HOUR_MS)))
    assert ratio_feature([candle(2 * HOUR_MS)], pos, "top_ls")[0] == math.log(1.5)
    assert raises(lambda: ratio_feature([candle(0)], pos, "oops"))


# ---------------- spot taker share and past return ----------------

def test_spot_taker_feature():
    candles = [candle(i * HOUR_MS, volume=10.0, buy=1.0 + i) for i in range(8)]
    out = spot_taker_feature(candles, hours=4)
    assert out[:3] == [None, None, None]
    assert close(out[3], (1 + 2 + 3 + 4) / 40.0)
    assert close(out[7], (5 + 6 + 7 + 8) / 40.0)
    zero = [candle(i * HOUR_MS, volume=0.0, buy=0.0) for i in range(6)]
    assert spot_taker_feature(zero, hours=4)[5] is None


def test_past_return_sign():
    closes = [100, 101, 102, 101, 100, 99, 100, 100]
    candles = [candle(i * HOUR_MS, close=c) for i, c in enumerate(closes)]
    assert past_return_sign(candles, hours=3) == [0, 0, 0, 1, -1, -1, -1, 0][:3] + [
        (closes[i] > closes[i - 3]) - (closes[i] < closes[i - 3]) for i in range(3, 8)
    ]


# ---------------- percentile signals ----------------

def test_percentile_signals_extremes_and_ties():
    rising = list(range(30))
    out = percentile_signals(rising, window=30, min_valid=10, high=0.9, low=0.1)
    assert out[:9] == [0] * 9
    assert all(v == 1 for v in out[10:])           # the newest value is always the top of a rising series

    falling = list(range(30, 0, -1))
    assert all(v == -1 for v in percentile_signals(falling, 30, 10)[10:])

    assert not any(percentile_signals([5.0] * 40, 30, 10))


def test_percentile_signals_window_eviction_and_missing_values():
    values = [float(i) for i in range(60)]
    out = percentile_signals(values, window=10, min_valid=5)
    assert all(v == 1 for v in out[5:])

    with_gaps = [None if i % 3 == 0 else float(i) for i in range(60)]
    out = percentile_signals(with_gaps, window=30, min_valid=5)
    assert all(out[i] == 0 for i in range(0, 60, 3))


def test_percentile_signals_have_no_lookahead_and_validate_input():
    rng = random.Random(1)
    values = [rng.gauss(0, 1) for _ in range(400)]
    full = percentile_signals(values, 100, 30)
    for n in (150, 273, 399):
        assert percentile_signals(values[:n], 100, 30) == full[:n]

    assert raises(lambda: percentile_signals([1.0], window=1))
    assert raises(lambda: percentile_signals([1.0], window=10, min_valid=20))
    assert raises(lambda: percentile_signals([1.0], high=0.2, low=0.8))


def test_gated_direction():
    assert gated_direction([1, 0, -1, 1], 1, [1, 1, -1, -1]) == [1, 0, 0, -1]
    assert gated_direction([1, 0, -1, 1], -1, [1, 1, -1, -1]) == [0, 0, -1, 0]
    assert raises(lambda: gated_direction([1], 1, [1, 1]))


# ---------------- event split ----------------

def test_split_events_purges_the_boundary():
    events = Events([10, 80, 91, 99, 100, 150], [1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
    first, second = split_events(events, cutoff_ms=100, hold_ms=10)
    assert first.timestamps == [10, 80] and first.edges == [1.0, 2.0]
    assert second.timestamps == [100, 150] and second.edges == [5.0, 6.0]


# ---------------- causality ----------------

def random_positioning(seed, hours):
    rng = random.Random(seed)
    funding = [(h * 8 * HOUR_MS, 8, rng.gauss(0.0001, 0.0001)) for h in range(hours // 8 + 2)]
    oi = 1000.0
    metrics = []
    for m in range(hours * 12 + 24):
        oi *= math.exp(rng.gauss(0, 0.001))
        metrics.append((m * FIVE_MIN_MS, oi, oi * 10, 1.0, math.exp(rng.gauss(0, 0.3)),
                        math.exp(rng.gauss(0, 0.3)), math.exp(rng.gauss(0, 0.5))))
    del metrics[200:230]            # a hole in the data
    return funding, metrics


def test_no_feature_uses_data_that_arrived_after_the_decision():
    hours = 120
    candles = walk(hours, seed=2)
    funding, metrics = random_positioning(3, hours)
    full = Positioning.from_rows(funding, metrics)

    makers = {
        "funding": lambda c, p: funding_feature(c, p),
        "oi": lambda c, p: open_interest_change_feature(c, p),
        "taker": lambda c, p: taker_flow_feature(c, p),
        "count": lambda c, p: ratio_feature(c, p, "count_ls"),
        "top": lambda c, p: ratio_feature(c, p, "top_ls"),
    }

    for k in (30, 55, 80, 119):
        t = candles[k].timestamp + HOUR_MS
        cut = Positioning.from_rows(
            [r for r in funding if r[0] <= t],
            [r for r in metrics if r[0] <= t - FIVE_MIN_MS],
        )
        for name, make in makers.items():
            assert make(candles[:k + 1], full)[k] == make(candles[:k + 1], cut)[k], (name, k)
