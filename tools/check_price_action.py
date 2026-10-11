"""
Falcon AI - F-004: do simple price-action signals carry a directional edge? (read-only)

Seven pre-registered variants, two assets. It trades nothing; edges are in basis
points BEFORE fees and are compared with an assumed round-trip cost. The
criteria are fixed in research/FINDINGS.md BEFORE the run and applied
mechanically here.

  S1/S2  liquidity sweep of the latest confirmed swing (strength 5 / 12), hold 24 candles
  S3-S5  session drift: long from the open of the Asia (00-08 UTC), Europe
         (08-16) and US (16-24) session to its close (hold 8 candles)
  S6     breakout out of a volatility compression, hold 24 candles
  S7     pullback against the 4h structure trend, hold 24 candles

A variant PASSES only if ALL hold:
  C0  at least 200 events on each asset
  C1  p < 0.05 / 7 on one asset and the same sign with p < 0.05 on the other
  C2  the sign holds in >= 70 % of usable years (>= 3 years with >= 20 events), both assets
  C3  the edge in its own direction is at least the assumed cost on both assets

Usage: python tools/check_price_action.py [SYMBOLS] [INTERVAL] [FLIPS]
       python tools/check_price_action.py BTCUSDT,ETHUSDT 1h 2000
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.data.history import CandleRepository  # noqa: E402
from src.market.timeframe import interval_to_ms  # noqa: E402
from src.validation.signal_scan import (  # noqa: E402
    breakout_signals,
    collect_events,
    evaluate_events,
    hour_signals,
    pullback_signals,
    sweep_signals,
)

SYMBOLS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["BTCUSDT", "ETHUSDT"]
INTERVAL = sys.argv[2] if len(sys.argv) > 2 else "1h"
FLIPS = int(sys.argv[3]) if len(sys.argv) > 3 else 2000

if INTERVAL != "1h":
    sys.exit("F-004 is defined for 1h candles only")

INTERVAL_MS = interval_to_ms(INTERVAL)
MIN_SEGMENT = 400

COST_BP = 12.0
MIN_EVENTS = 200
MIN_YEAR_SHARE = 0.70
MIN_YEARS = 3

VARIANTS = [
    ("S1 sweep strength 5", lambda seg: sweep_signals(seg, 5, INTERVAL), 24),
    ("S2 sweep strength 12", lambda seg: sweep_signals(seg, 12, INTERVAL), 24),
    ("S3 session Asia", lambda seg: hour_signals(seg, 23), 8),
    ("S4 session Europe", lambda seg: hour_signals(seg, 7), 8),
    ("S5 session US", lambda seg: hour_signals(seg, 15), 8),
    ("S6 compression breakout", lambda seg: breakout_signals(seg), 24),
    ("S7 pullback vs 4h trend", lambda seg: pullback_signals(seg, INTERVAL_MS), 24),
]

ALPHA = 0.05 / len(VARIANTS)


def sign(value):
    return (value > 0) - (value < 0)


def years_ok(result):
    return result.years_usable >= MIN_YEARS and result.years_same_sign / result.years_usable >= MIN_YEAR_SHARE


def judge(first, second):

    c0 = first.events >= MIN_EVENTS and second.events >= MIN_EVENTS
    same = sign(first.mean_edge) == sign(second.mean_edge) != 0
    c1 = same and any(
        a.p_value < ALPHA and b.p_value < 0.05 for a, b in ((first, second), (second, first))
    )
    c2 = years_ok(first) and years_ok(second)
    c3 = same and abs(first.mean_edge) >= COST_BP and abs(second.mean_edge) >= COST_BP

    return c0, c1, c2, c3


def main():

    print(f"{','.join(SYMBOLS)} {INTERVAL}: {len(VARIANTS)} variants, p must be < {ALPHA:.4f} (0.05 / {len(VARIANTS)}, Bonferroni)")
    print(f"edges in bp before fees; assumed round-trip cost {COST_BP:.0f} bp; {FLIPS} block sign flips (weekly blocks)")
    print()

    segments = {}

    with CandleRepository() as repo:
        for symbol in SYMBOLS:
            segments[symbol] = [s for s in repo.segments(symbol, INTERVAL) if len(s) >= MIN_SEGMENT]

    results = {}

    for name, make, horizon in VARIANTS:

        for symbol in SYMBOLS:

            started = time.time()
            events = collect_events(segments[symbol], make, horizon)
            results[(name, symbol)] = evaluate_events(events, FLIPS)
            r = results[(name, symbol)]
            print(
                f"{name:<26} {symbol[:3]} events {r.events:>5} edge {r.mean_edge:+7.2f}bp "
                f"hit {r.hit_rate * 100:4.1f}% p={r.p_value:.4f} yrs {r.years_same_sign}/{r.years_usable} "
                f"({time.time() - started:.0f}s)"
            )

    print()
    print("=" * 70)

    passed = []

    if len(SYMBOLS) < 2:
        print("Only one symbol given: cross-asset criteria cannot be evaluated.")
    else:
        first, second = SYMBOLS[0], SYMBOLS[1]

        for name, _, _ in VARIANTS:

            c0, c1, c2, c3 = judge(results[(name, first)], results[(name, second)])
            ok = c0 and c1 and c2 and c3
            print(
                f"{name:<26} C0 events {'ok' if c0 else 'no'} | C1 p-value {'ok' if c1 else 'no'} "
                f"| C2 years {'ok' if c2 else 'no'} | C3 beats cost {'ok' if c3 else 'no'} -> {'PASS' if ok else 'fail'}"
            )

            if ok:
                passed.append(name)

    print("=" * 70)

    if not passed:
        print("RESULT F-004: none of the pre-registered price-action signals has a tradable edge.")
    else:
        for name in passed:
            print(f"PASSES: {name}")
        print("A pass is a lead: confirm on data not used here, with real fees, before using it.")

    print("DONE")


main()
