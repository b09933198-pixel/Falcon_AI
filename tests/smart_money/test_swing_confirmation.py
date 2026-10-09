"""
Tests for swing confirmation and no-lookahead behaviour.

The candles here are small hand-made or seeded-random fixtures used to test
logic (ties, confirmation, prefix consistency). They are not numerical
validation data.
"""

import random

from src.analysis.smart_money import SwingDetectorEngine
from src.analysis.smart_money.swing_detector import confirmed_swings
from src.domain.models import Candle


def candle(high, low, ts=0):
    return Candle(
        timestamp=ts, open=low, high=high, low=low, close=high,
        volume=0, quote_volume=0, trades=0, buy_volume=0, buy_quote_volume=0,
    )


def series(highs, lows):
    return [candle(h, l, ts=i * 1000) for i, (h, l) in enumerate(zip(highs, lows))]


def random_walk(n, seed):
    rng = random.Random(seed)
    price = 1000.0
    out = []
    for i in range(n):
        price += rng.uniform(-10, 10)
        spread = rng.uniform(1, 8)
        out.append(candle(price + spread, price - spread, ts=i * 1000))
    return out


def key(swing):
    return (swing.index, swing.is_high, swing.price)


def test_confirmed_index_is_index_plus_strength():
    candles = series(
        [10, 12, 15, 20, 30, 18, 15, 12, 10],
        [5, 6, 7, 8, 9, 8, 7, 6, 5],
    )
    swings = SwingDetectorEngine().detect(candles, strength=2)
    high = [s for s in swings if s.is_high][0]
    assert high.index == 4
    assert high.confirmed_index == 6


def test_equal_highs_give_exactly_one_swing_at_the_first_candle():
    candles = series(
        [10, 12, 20, 20, 12, 10, 9],
        [5, 6, 7, 7, 6, 5, 4],
    )
    swings = [s for s in SwingDetectorEngine().detect(candles, strength=2) if s.is_high]
    assert [s.index for s in swings] == [2]


def test_outside_bar_returns_both_high_and_low():
    candles = series(
        [10, 11, 30, 11, 10],
        [8, 9, 1, 9, 8],
    )
    swings = SwingDetectorEngine().detect(candles, strength=2)
    kinds = sorted((s.index, s.is_high) for s in swings)
    assert kinds == [(2, False), (2, True)]


def test_too_short_series_returns_nothing():
    candles = series([1, 2, 3, 2], [0, 1, 2, 1])
    assert SwingDetectorEngine().detect(candles, strength=2) == []


def test_invalid_strength_is_rejected():
    for bad in (0, -1, 1.5, "2", None):
        try:
            SwingDetectorEngine().detect(series([1, 2, 3], [0, 1, 2]), strength=bad)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for strength={bad!r}")


def test_last_candles_can_never_be_swings():
    candles = random_walk(300, seed=1)
    for strength in (1, 2, 5):
        swings = SwingDetectorEngine().detect(candles, strength=strength)
        assert all(s.index <= len(candles) - 1 - strength for s in swings)
        assert all(s.confirmed_index <= len(candles) - 1 for s in swings)


def test_timeframe_and_timestamp_are_carried():
    candles = series([10, 12, 15, 20, 30, 18, 15, 12, 10], [5, 6, 7, 8, 9, 8, 7, 6, 5])
    swings = SwingDetectorEngine().detect(candles, strength=2, timeframe="1h")
    assert swings[0].timeframe == "1h"
    assert swings[0].timestamp == 4000


def test_confirmed_swings_filters_by_knowledge():
    candles = random_walk(200, seed=2)
    swings = SwingDetectorEngine().detect(candles, strength=3)
    for index in (10, 50, 120, 199):
        visible = confirmed_swings(swings, index)
        assert all(s.confirmed_index <= index for s in visible)


def test_no_lookahead_prefix_matches_full_run():
    """Detecting on candles[:n] must equal the full run restricted to what
    was already confirmed at candle n-1. This is the no-lookahead guarantee."""

    detector = SwingDetectorEngine()

    for seed in (3, 4, 5):
        candles = random_walk(400, seed=seed)

        for strength in (1, 2, 4):
            full = detector.detect(candles, strength=strength)

            for n in (15, 60, 133, 250, 399):
                prefix = detector.detect(candles[:n], strength=strength)
                expected = confirmed_swings(full, n - 1)
                assert [key(s) for s in prefix] == [key(s) for s in expected], (
                    seed, strength, n
                )
