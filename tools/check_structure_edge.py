"""
Falcon AI - does market structure say anything about the price that follows? (read-only)

For each swing strength and horizon it measures the forward return after a
BULLISH state versus after a BEARISH state, and asks how often a difference
that large appears when the states are slid against the returns (see
src/validation/forward_test.py for the exact conventions).

This is a MEASUREMENT. It includes no fees or slippage and it is not a strategy.

Usage: python tools/check_structure_edge.py [SYMBOL] [INTERVAL] [SHIFTS]
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.analysis.smart_money import StructureType  # noqa: E402
from src.data.history import CandleRepository  # noqa: E402
from src.validation import (  # noqa: E402
    circular_shift_test,
    collect_samples,
    group_means,
    returns_by_year,
    signed_edge,
)

SYMBOL = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
INTERVAL = sys.argv[2] if len(sys.argv) > 2 else "1h"
SHIFTS = int(sys.argv[3]) if len(sys.argv) > 3 else 1000

STRENGTHS = (3, 5, 8, 12)
HORIZONS = (4, 24)
MIN_SEGMENT = 200
UP = StructureType.BULLISH
DOWN = StructureType.BEARISH


def main():
    with CandleRepository() as repo:
        segments = [s for s in repo.segments(SYMBOL, INTERVAL) if len(s) >= MIN_SEGMENT]

    total = sum(len(s) for s in segments)
    tests = len(STRENGTHS) * len(HORIZONS)
    alpha = 0.05 / tests

    print(f"{SYMBOL} {INTERVAL}: {len(segments)} segments, {total} candles, {SHIFTS} shifts per test")
    print(f"{tests} tests -> a result counts only if p < {alpha:.4f} (0.05 / {tests}, Bonferroni)")
    print("returns are in basis points (1 bp = 0.01%), entry = next open, no fees")
    print()

    cache = {}
    survivors = []

    for horizon in HORIZONS:

        first = collect_samples(segments, STRENGTHS[0], horizon, INTERVAL, cache)
        drift = sum(first.returns) / len(first.returns)
        print(f"horizon {horizon} candles: unconditional mean forward return {drift:+.2f} bp (n={len(first)})")

        for strength in STRENGTHS:
            started = time.time()
            samples = collect_samples(segments, strength, horizon, INTERVAL, cache)

            n_up, n_down, m_up, m_down = group_means(samples.states, samples.returns, UP, DOWN)
            observed, p = circular_shift_test(
                samples.states, samples.returns, UP, DOWN, shifts=SHIFTS
            )
            signed = signed_edge(samples.states, samples.returns, UP, DOWN)

            years = returns_by_year(samples.timestamps, samples.states, samples.returns, UP, DOWN)
            usable = [v for v in years.values() if v is not None]
            positive = sum(1 for v in usable if v > 0)

            mark = "  <== passes" if p < alpha else ""
            print(
                f"  strength={strength:>2} | bull n={n_up} {m_up:+.2f} bp | bear n={n_down} {m_down:+.2f} bp "
                f"| diff {observed:+.2f} bp p={p:.4f} | long/short {signed:+.2f} bp "
                f"| years diff>0: {positive}/{len(usable)} | {time.time() - started:.0f}s{mark}"
            )

            if p < alpha:
                survivors.append((strength, horizon, observed, p, positive, len(usable)))

        print()

    print("=" * 60)

    if not survivors:
        print("RESULT: no combination passes the corrected threshold.")
        print("Reading: in this data, bullish/bearish structure does not separate")
        print("the price that follows any better than chance.")
    else:
        for strength, horizon, observed, p, positive, usable in survivors:
            print(
                f"PASSES: strength={strength} horizon={horizon} diff {observed:+.2f} bp "
                f"p={p:.4f} (years positive {positive}/{usable})"
            )
        print("A pass is a lead, not a strategy: check fees, then test on data not used here.")

    print("DONE")


main()
