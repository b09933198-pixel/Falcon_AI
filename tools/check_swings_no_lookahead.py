"""
Falcon AI - real-data check: swing detection must never look ahead (read-only).

For several random cut-off points, detection on the data up to that point must
equal the full-history detection restricted to swings already confirmed then.

Usage: python tools/check_swings_no_lookahead.py [SYMBOL] [INTERVAL]
"""

import os
import random
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.analysis.smart_money import SwingDetectorEngine  # noqa: E402
from src.analysis.smart_money.swing_detector import confirmed_swings  # noqa: E402
from src.data.history import CandleRepository  # noqa: E402

SYMBOL = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
INTERVAL = sys.argv[2] if len(sys.argv) > 2 else "1h"
STRENGTHS = (2, 3, 5)
WINDOW = 4000
CUTOFFS = 40


def key(swing):
    return (swing.index, swing.is_high, swing.price)


def main():
    with CandleRepository() as repo:
        segments = list(repo.segments(SYMBOL, INTERVAL))

    segment = max(segments, key=len)
    candles = segment[-WINDOW:]

    print(f"{SYMBOL} {INTERVAL}: {len(segments)} segments, longest {len(segment)} candles")
    print(f"checking the last {len(candles)} candles of the longest segment")

    detector = SwingDetectorEngine()
    total_bad = 0

    for strength in STRENGTHS:
        started = time.time()
        full = detector.detect(candles, strength=strength, timeframe=INTERVAL)
        highs = sum(1 for s in full if s.is_high)
        lows = len(full) - highs

        rng = random.Random(7)
        cutoffs = sorted(rng.sample(range(strength * 2 + 1, len(candles)), CUTOFFS))

        bad = 0
        for n in cutoffs:
            prefix = detector.detect(candles[:n], strength=strength, timeframe=INTERVAL)
            expected = confirmed_swings(full, n - 1)
            if [key(s) for s in prefix] != [key(s) for s in expected]:
                bad += 1

        total_bad += bad
        per100 = len(full) / len(candles) * 100
        print(
            f"  strength={strength}: swings={len(full)} (highs {highs}, lows {lows}) "
            f"| {per100:.1f} per 100 candles | mismatches {bad}/{CUTOFFS} "
            f"| {time.time() - started:.1f}s"
        )

    if total_bad:
        print("RESULT: LOOKAHEAD DETECTED")
        sys.exit(1)

    print("RESULT: NO LOOKAHEAD - OK")


main()
