"""
Tests for the market structure tracker.

Hand-made swing sequences and seeded-random candles test LOGIC (alternation,
labels, trend, causality). They are not numerical validation data.
"""

import random

from src.analysis.smart_money import (
    StructureTracker,
    StructureType,
    SwingBuilder,
    SwingDetectorEngine,
    SwingLabel,
    confirmed_swings,
    structure_at,
    structure_timeline,
    trend_at,
)
from src.domain.models import Candle


def high(index, price):
    return SwingBuilder.high(index=index, price=price, strength=1)


def low(index, price):
    return SwingBuilder.low(index=index, price=price, strength=1)


def feed(swings):
    tracker = StructureTracker()
    for swing in swings:
        tracker.update(swing)
    return tracker


def labels(tracker):
    return [(s.swing.is_high, s.swing.price, s.label) for s in tracker.sequence]


def test_consecutive_highs_keep_the_higher_one():
    t = feed([high(1, 100), high(3, 110), high(5, 105), low(7, 90)])
    assert [(s.swing.is_high, s.swing.price) for s in t.sequence] == [(True, 110), (False, 90)]


def test_consecutive_lows_keep_the_lower_one():
    t = feed([high(1, 100), low(3, 90), low(5, 85), low(7, 88)])
    assert [(s.swing.is_high, s.swing.price) for s in t.sequence] == [(True, 100), (False, 85)]


def test_tie_keeps_the_earlier_swing():
    t = feed([high(1, 100), high(3, 100)])
    assert [s.swing.index for s in t.sequence] == [1]


def test_labels_and_bullish_trend():
    t = feed([high(1, 100), low(3, 90), high(5, 110), low(7, 95)])
    assert labels(t) == [
        (True, 100, SwingLabel.FIRST),
        (False, 90, SwingLabel.FIRST),
        (True, 110, SwingLabel.HH),
        (False, 95, SwingLabel.HL),
    ]
    assert t.trend == StructureType.BULLISH


def test_bearish_trend():
    t = feed([high(1, 100), low(3, 90), high(5, 95), low(7, 80)])
    assert t.trend == StructureType.BEARISH


def test_mixed_labels_are_ranging():
    t = feed([high(1, 100), low(3, 90), high(5, 110), low(7, 85)])
    assert t.trend == StructureType.RANGING


def test_equal_levels_are_ranging():
    t = feed([high(1, 100), low(3, 90), high(5, 100), low(7, 90)])
    assert [s.label for s in t.sequence][2:] == [SwingLabel.EQ, SwingLabel.EQ]
    assert t.trend == StructureType.RANGING


def test_unknown_until_two_highs_and_two_lows():
    assert feed([]).trend == StructureType.UNKNOWN
    assert feed([high(1, 100), low(3, 90)]).trend == StructureType.UNKNOWN
    assert feed([high(1, 100), low(3, 90), high(5, 110)]).trend == StructureType.UNKNOWN


def test_replacing_the_last_swing_relabels_it():
    t = feed([high(1, 100), low(3, 90), high(5, 105), high(7, 120)])
    assert labels(t)[-1] == (True, 120, SwingLabel.HH)
    assert len(t.sequence) == 3


def test_swings_must_arrive_in_confirmation_order():
    t = StructureTracker()
    t.update(high(10, 100))
    try:
        t.update(low(3, 90))
    except ValueError:
        return
    raise AssertionError("expected ValueError")


def test_outside_bar_pair_at_the_same_index_is_accepted():
    t = feed([high(5, 110), low(5, 80), high(9, 120), low(11, 85)])
    assert [s.swing.is_high for s in t.sequence] == [True, False, True, False]


def candle(high_, low_, ts):
    return Candle(
        timestamp=ts, open=low_, high=high_, low=low_, close=high_,
        volume=0, quote_volume=0, trades=0, buy_volume=0, buy_quote_volume=0,
    )


def random_walk(n, seed):
    rng = random.Random(seed)
    price = 1000.0
    out = []
    for i in range(n):
        price += rng.uniform(-10, 10)
        spread = rng.uniform(1, 8)
        out.append(candle(price + spread, price - spread, i * 1000))
    return out


def snapshot(tracker):
    return ([(s.swing.index, s.swing.is_high, s.swing.price, s.label) for s in tracker.sequence],
            tracker.trend)


def test_incremental_timeline_matches_recomputation_from_scratch():
    candles = random_walk(500, seed=21)
    for strength in (1, 3):
        swings = SwingDetectorEngine().detect(candles, strength=strength)
        timeline = structure_timeline(swings)
        for i, (confirmed_index, trend) in enumerate(timeline):
            fresh = structure_at(swings, confirmed_index)
            assert fresh.trend == timeline_trend_after(timeline, i), (strength, i)


def timeline_trend_after(timeline, i):
    # last entry sharing the same confirmed_index describes the state at that candle
    j = i
    while j + 1 < len(timeline) and timeline[j + 1][0] == timeline[i][0]:
        j += 1
    return timeline[j][1]


def test_trend_at_lookup():
    swings = [high(1, 100), low(3, 90), high(5, 110), low(7, 95)]
    timeline = structure_timeline(swings)
    assert trend_at(timeline, 0) == StructureType.UNKNOWN
    assert trend_at(timeline, 7) == StructureType.UNKNOWN
    assert trend_at(timeline, 8) == StructureType.BULLISH
    assert trend_at(timeline, 10_000) == StructureType.BULLISH


def test_structure_has_no_lookahead():
    """Structure built from candles[:n] must equal structure from the full run
    restricted to swings confirmed by candle n-1."""

    detector = SwingDetectorEngine()

    for seed in (31, 32, 33):
        candles = random_walk(500, seed=seed)

        for strength in (1, 3):
            full = detector.detect(candles, strength=strength)

            for n in (20, 77, 150, 311, 499):
                prefix = detector.detect(candles[:n], strength=strength)
                from_prefix = feed(prefix)
                from_full = structure_at(full, n - 1)
                assert snapshot(from_prefix) == snapshot(from_full), (seed, strength, n)
                assert trend_at(structure_timeline(full), n - 1) == from_prefix.trend, (
                    seed, strength, n
                )
