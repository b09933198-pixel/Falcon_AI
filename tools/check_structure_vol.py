"""
Falcon AI - F-002: is volatility predictable, and does market structure add to it? (read-only)

Part V-1  How much of the next-24-candle volatility is predicted by PAST
          volatility and the time of day alone (baseline model)?
Part F-002 Does a market-structure feature add information beyond that baseline?

This is a MEASUREMENT. It trades nothing and includes no fees.
Criteria are fixed in research/FINDINGS.md BEFORE the run and applied here
mechanically, so the verdict cannot be tuned after seeing results.

Usage: python tools/check_structure_vol.py [SYMBOLS] [INTERVAL] [SHIFTS]
       python tools/check_structure_vol.py BTCUSDT,ETHUSDT 1h 1000
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.data.history import CandleRepository  # noqa: E402
from src.validation.volatility_test import (  # noqa: E402
    FEATURE_NAMES,
    analyze_feature,
    baseline_report,
    build_dataset,
)

SYMBOLS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["BTCUSDT", "ETHUSDT"]
INTERVAL = sys.argv[2] if len(sys.argv) > 2 else "1h"
SHIFTS = int(sys.argv[3]) if len(sys.argv) > 3 else 1000

STRENGTHS = (5, 12)
HORIZON = 24
FAST, SLOW = 24, 168
MIN_SEGMENT = 400

TESTS = len(STRENGTHS) * len(FEATURE_NAMES)
ALPHA = 0.05 / TESTS
MIN_YEAR_SHARE = 0.70
MIN_OOS_GAIN = 0.005
MIN_BASELINE_R2 = 0.10


def sign(value):
    return (value > 0) - (value < 0)


def year_check(result):
    return result.years_usable >= 3 and result.years_same_sign / result.years_usable >= MIN_YEAR_SHARE


def evaluate(first, second):
    """Apply the four fixed criteria to the results on two assets."""

    c1 = any(
        a.p_value < ALPHA and sign(a.correlation) == sign(b.correlation) != 0 and b.p_value < 0.05
        for a, b in ((first, second), (second, first))
    )
    c2 = year_check(first) and year_check(second)
    c3 = first.oos_gain >= MIN_OOS_GAIN and second.oos_gain >= MIN_OOS_GAIN

    return c1, c2, c3


def main():
    results = {}
    baseline = {}
    rows = {}

    print(f"{','.join(SYMBOLS)} {INTERVAL}: horizon {HORIZON} candles, windows {FAST}/{SLOW}, {SHIFTS} shifts per test")
    print(f"{TESTS} feature tests -> p must be < {ALPHA:.4f} (0.05 / {TESTS}, Bonferroni)")
    print("target = ln(mean candle range over the next candles); features use confirmed swings only")
    print()

    for symbol in SYMBOLS:

        with CandleRepository() as repo:
            segments = [s for s in repo.segments(symbol, INTERVAL) if len(s) >= MIN_SEGMENT]

        cache = {}

        for strength in STRENGTHS:

            started = time.time()
            data = build_dataset(segments, strength, HORIZON, FAST, SLOW, INTERVAL, cache)
            rows[(symbol, strength)] = len(data)

            if strength == STRENGTHS[0]:
                baseline[symbol] = baseline_report(data)

            for name in FEATURE_NAMES:
                results[(symbol, strength, name)] = analyze_feature(data, name, SHIFTS)

            print(f"{symbol} strength={strength}: {len(data)} rows, done in {time.time() - started:.0f}s")

    print()
    print("=" * 70)
    print("V-1  baseline: past volatility + time of day -> next volatility")

    usable = True

    for symbol in SYMBOLS:
        in_sample, out_sample = baseline[symbol]
        usable = usable and out_sample >= MIN_BASELINE_R2
        print(f"  {symbol}: R2 in-sample {in_sample:.3f} | out-of-sample (last 30%) {out_sample:.3f}")

    print(f"  verdict: {'volatility IS forecastable enough for risk sizing' if usable else 'NOT forecastable enough'}"
          f" (needs out-of-sample R2 >= {MIN_BASELINE_R2} on every asset)")

    print()
    print("F-002  does structure add information beyond the baseline?")

    for strength in STRENGTHS:
        for name in FEATURE_NAMES:
            print(f"  strength={strength:>2} {name:<8}", end="")
            for symbol in SYMBOLS:
                r = results[(symbol, strength, name)]
                print(
                    f" | {symbol[:3]} corr {r.correlation:+.3f} p={r.p_value:.4f} "
                    f"yrs {r.years_same_sign}/{r.years_usable} oosgain {r.oos_gain:+.4f}",
                    end="",
                )
            print()

    print()

    passed = []

    if len(SYMBOLS) < 2:
        print("Only one symbol given: cross-asset criteria cannot be evaluated.")
    else:
        first, second = SYMBOLS[0], SYMBOLS[1]

        for strength in STRENGTHS:
            for name in FEATURE_NAMES:
                c1, c2, c3 = evaluate(
                    results[(first, strength, name)], results[(second, strength, name)]
                )
                ok = c1 and c2 and c3
                print(
                    f"  strength={strength:>2} {name:<8} "
                    f"C1 p-value {'ok' if c1 else 'no'} | C2 years {'ok' if c2 else 'no'} "
                    f"| C3 out-of-sample gain {'ok' if c3 else 'no'} -> {'PASS' if ok else 'fail'}"
                )
                if ok:
                    passed.append((strength, name))

    print("=" * 70)

    if not passed:
        print("RESULT F-002: no structure feature adds information beyond past volatility.")
    else:
        for strength, name in passed:
            print(f"PASSES: strength={strength} feature={name}")
        print("A pass is a lead: confirm on data not used here before using it.")

    print("DONE")


main()
