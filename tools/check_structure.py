"""
Falcon AI - real-data report for market structure (read-only).

For several swing strengths it prints how noisy the structure is, compares it
with a shuffled copy of the same candles (a no-structure baseline), and checks
on real candles that structure never uses information from the future.

Usage: python tools/check_structure.py [SYMBOL] [INTERVAL]
"""

import os
import random
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.analysis.smart_money import (  # noqa: E402
    StructureType,
    SwingDetectorEngine,
    structure_at,
    structure_timeline,
)
from src.data.history import CandleRepository  # noqa: E402
from src.domain.models import Candle  # noqa: E402

SYMBOL = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
INTERVAL = sys.argv[2] if len(sys.argv) > 2 else "1h"
STRENGTHS = (2, 3, 5, 8, 12)
CHECK_WINDOW = 6000
CUTOFFS = 30

DETECTOR = SwingDetectorEngine()


def snapshot(tracker):
    return (
        [(s.swing.index, s.swing.is_high, s.swing.price, s.label) for s in tracker.sequence],
        tracker.trend,
    )


def shuffled(candles, seed=5):
    """Same candle shapes in random order: keeps volatility, destroys serial order."""

    shapes = [(c.high / c.open, c.low / c.open, c.close / c.open) for c in candles]
    random.Random(seed).shuffle(shapes)

    out = []
    price = candles[0].open

    for i, (h, l, cl) in enumerate(shapes):
        out.append(Candle(
            timestamp=candles[i].timestamp,
            open=price, high=price * h, low=price * l, close=price * cl,
            volume=0, quote_volume=0, trades=0, buy_volume=0, buy_quote_volume=0,
        ))
        price = price * cl

    return out


def profile(candles, strength):
    swings = DETECTOR.detect(candles, strength=strength, timeframe=INTERVAL)
    timeline = structure_timeline(swings)
    total = len(candles)

    spent = {state: 0 for state in StructureType}
    spent[StructureType.UNKNOWN] += timeline[0][0] if timeline else total

    runs = 0
    previous = None

    for i, (confirmed_index, trend) in enumerate(timeline):
        end = timeline[i + 1][0] if i + 1 < len(timeline) else total
        spent[trend] += max(0, end - confirmed_index)
        if trend != previous and trend != StructureType.UNKNOWN:
            runs += 1
        previous = trend

    share = {k: v / total * 100 for k, v in spent.items()}
    avg_run = total / runs if runs else 0

    return swings, structure_at(swings, total - 1), share, runs, avg_run


def main():
    with CandleRepository() as repo:
        segments = list(repo.segments(SYMBOL, INTERVAL))

    candles = max(segments, key=len)
    print(f"{SYMBOL} {INTERVAL}: {len(segments)} segments, using the longest ({len(candles)} candles)")

    baseline = shuffled(candles)
    window = candles[-CHECK_WINDOW:]
    total_bad = 0

    for strength in STRENGTHS:
        started = time.time()

        swings, final, share, runs, avg_run = profile(candles, strength)
        _, _, _, _, shuffled_run = profile(baseline, strength)

        full = DETECTOR.detect(window, strength=strength, timeframe=INTERVAL)
        rng = random.Random(11)
        cutoffs = sorted(rng.sample(range(strength * 4 + 2, len(window)), CUTOFFS))

        bad = 0
        for n in cutoffs:
            prefix = DETECTOR.detect(window[:n], strength=strength, timeframe=INTERVAL)
            if snapshot(structure_at(prefix, n - 1)) != snapshot(structure_at(full, n - 1)):
                bad += 1
        total_bad += bad

        print(
            f"strength={strength:>2}: swings={len(swings)} kept={len(final.sequence)} "
            f"| bull {share[StructureType.BULLISH]:.0f}% bear {share[StructureType.BEARISH]:.0f}% "
            f"range {share[StructureType.RANGING]:.0f}%"
        )
        print(
            f"            state changes={runs} (avg {avg_run:.0f} candles per state; "
            f"shuffled baseline {shuffled_run:.0f}) "
            f"| lookahead mismatches {bad}/{CUTOFFS} | {time.time() - started:.1f}s"
        )

    if total_bad:
        print("RESULT: LOOKAHEAD DETECTED")
        sys.exit(1)

    print("RESULT: NO LOOKAHEAD - OK")


main()
