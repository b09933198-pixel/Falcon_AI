"""
Falcon AI - F-003: is the volatility forecaster good enough for risk use? (read-only)

Walk-forward test of src/analysis/volatility/forecaster.py. It trades nothing and includes no
fees. The five criteria are fixed in research/FINDINGS.md BEFORE the run and
applied mechanically here.

  W1  beats the best naive forecast: model MSE <= 0.97 x best naive MSE, both assets
  W2  calibration slope (realised on predicted, log space) within [0.90, 1.10], both assets
  W3  resolution: top-decile realised range >= 1.5 x bottom-decile, and at least
      8 of 9 decile steps rising, both assets
  W4  model beats the best naive in >= 75 % of test years (>= 3 years with
      >= 2000 rows), both assets
  W5  the 90 % upper bound holds 86 %-94 % of the time, both assets

Usage: python tools/check_vol_forecast.py [SYMBOLS] [INTERVAL]
       python tools/check_vol_forecast.py BTCUSDT,ETHUSDT 1h
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.data.history import CandleRepository  # noqa: E402
from src.market.timeframe import interval_to_ms  # noqa: E402
from src.analysis.volatility import build_table  # noqa: E402
from src.validation.vol_walkforward import (  # noqa: E402
    calibration_slope,
    coverage,
    decile_table,
    mse,
    rising_steps,
    walk_forward,
    yearly_comparison,
)

SYMBOLS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["BTCUSDT", "ETHUSDT"]
INTERVAL = sys.argv[2] if len(sys.argv) > 2 else "1h"

HORIZON = 24
MIN_SEGMENT = 400
TRAIN_YEARS = 2
REFIT_DAYS = 90

MAX_MSE_RATIO = 0.97
SLOPE_RANGE = (0.90, 1.10)
MIN_DECILE_RATIO = 1.5
MIN_RISING_STEPS = 8
MIN_YEAR_SHARE = 0.75
MIN_YEARS = 3
COVERAGE_RANGE = (0.86, 0.94)
YEAR_MIN_ROWS = 2000

DAY_MS = 86_400_000


def analyse(symbol):

    interval_ms = interval_to_ms(INTERVAL)

    with CandleRepository() as repo:
        segments = [s for s in repo.segments(symbol, INTERVAL) if len(s) >= MIN_SEGMENT]

    table = build_table(segments, horizon=HORIZON)

    result = walk_forward(
        table,
        interval_ms,
        horizon=HORIZON,
        min_train_rows=TRAIN_YEARS * 365 * DAY_MS // interval_ms,
        refit_rows=REFIT_DAYS * DAY_MS // interval_ms,
    )

    naive = result.naive
    model_mse = mse(result.y, result.pred)
    naive_mse = {name: mse(result.y, series) for name, series in naive.items()}
    best_name = min(naive_mse, key=naive_mse.get)

    deciles = decile_table(result.pred, result.y)
    realised = [row[1] for row in deciles]

    years = yearly_comparison(
        result.timestamps, result.y, result.pred, list(naive.values()), YEAR_MIN_ROWS
    )
    wins = sum(1 for m, b in years.values() if m < b)

    return {
        "rows": len(table),
        "test_rows": len(result),
        "folds": result.folds,
        "model_mse": model_mse,
        "naive_mse": naive_mse,
        "best": best_name,
        "ratio": model_mse / naive_mse[best_name],
        "slope": calibration_slope(result.pred, result.y),
        "deciles": deciles,
        "decile_ratio": realised[-1] / realised[0],
        "rising": rising_steps(realised),
        "coverage": coverage(result.y, result.upper),
        "years": years,
        "wins": wins,
    }


def verdicts(r):

    w1 = r["ratio"] <= MAX_MSE_RATIO
    w2 = SLOPE_RANGE[0] <= r["slope"] <= SLOPE_RANGE[1]
    w3 = r["decile_ratio"] >= MIN_DECILE_RATIO and r["rising"] >= MIN_RISING_STEPS
    w4 = len(r["years"]) >= MIN_YEARS and r["wins"] / len(r["years"]) >= MIN_YEAR_SHARE
    w5 = COVERAGE_RANGE[0] <= r["coverage"] <= COVERAGE_RANGE[1]

    return w1, w2, w3, w4, w5


def main():

    print(f"{','.join(SYMBOLS)} {INTERVAL}: walk-forward, train >= {TRAIN_YEARS}y, refit every {REFIT_DAYS}d, horizon {HORIZON}")
    print("naive references get the same bias correction; training rows overlapping the test period are purged")
    print()

    reports = {}

    for symbol in SYMBOLS:
        started = time.time()
        reports[symbol] = analyse(symbol)
        print(f"{symbol}: done in {time.time() - started:.0f}s")

    labels = ("W1 beats naive", "W2 calibration", "W3 resolution", "W4 yearly wins", "W5 90% bound")
    all_ok = [True] * 5

    for symbol in SYMBOLS:

        r = reports[symbol]
        checks = verdicts(r)

        print()
        print("=" * 70)
        print(f"{symbol}: {r['rows']} rows, {r['test_rows']} out-of-sample rows in {r['folds']} folds")
        print(f"  MSE model {r['model_mse']:.4f} | " + " | ".join(f"{k} {v:.4f}" for k, v in r["naive_mse"].items()))
        print(f"  ratio model / best naive ({r['best']}): {r['ratio']:.3f}   (needs <= {MAX_MSE_RATIO})")
        print(f"  calibration slope: {r['slope']:.3f}   (needs {SLOPE_RANGE[0]}..{SLOPE_RANGE[1]})")
        print("  deciles (predicted range -> realised range, in basis points):")
        for k, (p, a) in enumerate(r["deciles"], 1):
            print(f"    {k:>2}: {p * 10000:7.1f} -> {a * 10000:7.1f}")
        print(f"  top/bottom realised ratio {r['decile_ratio']:.2f} (needs >= {MIN_DECILE_RATIO}), rising steps {r['rising']}/9 (needs >= {MIN_RISING_STEPS})")
        print(f"  90% upper bound held {r['coverage'] * 100:.1f}% of the time (needs {COVERAGE_RANGE[0] * 100:.0f}-{COVERAGE_RANGE[1] * 100:.0f}%)")
        print("  years (model MSE vs best naive MSE):")
        for year, (m, b) in r["years"].items():
            print(f"    {year}: {m:.4f} vs {b:.4f} -> {'model' if m < b else 'naive'}")
        print(f"  year wins {r['wins']}/{len(r['years'])} (needs >= {MIN_YEAR_SHARE * 100:.0f}% and >= {MIN_YEARS} years)")
        print("  " + " | ".join(f"{lab}: {'ok' if ok else 'NO'}" for lab, ok in zip(labels, checks)))

        all_ok = [a and c for a, c in zip(all_ok, checks)]

    print()
    print("=" * 70)
    print("SUMMARY (all assets must pass): " + " | ".join(f"{lab}: {'ok' if ok else 'NO'}" for lab, ok in zip(labels, all_ok)))

    if all(all_ok):
        print("RESULT F-003: the volatility forecaster is validated for risk use on this data.")
    else:
        print("RESULT F-003: NOT validated; the failed criteria above say what is wrong.")

    print("DONE")


main()
