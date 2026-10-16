"""
Falcon AI - F-007: per-level adverse-excursion quantiles (risk sheet v2) (read-only)

Same test as tools/check_excursion.py (F-006), but the ratio quantiles
E / expected_range are estimated separately for each risk level
(walk_forward_levels). It forecasts no direction, trades nothing and includes
no fees. The criteria are fixed in research/FINDINGS.md (F-007), committed
BEFORE this tool was written, and applied mechanically here. F-007 was designed
after seeing F-006 on the same data (disclosed in the ledger).

  R1-R5 exactly as in F-006, plus
  R6  R2 holds separately in each half of the test period (before / from 2025-01-01),
      both assets, for every level with >= 300 events in that half

  R1  pooled coverage on both assets: q50 in [47,53]%, q80 in [77,83]%, q95 in [92,98]%
  R2  coverage by risk level (levels with >= 300 events): q80 and q95 within +-6 pp of nominal, both assets
  R3  q95 coverage in [90,99]% in every calendar year with >= 1000 events, both assets
  R4  median realised E rises strictly low < normal < high < extreme, both assets
  R5  pinball loss at q80 and q95 lower than baseline B (trailing 365-day unconditional quantile), both assets

Usage: python tools/check_excursion_v2.py [SYMBOLS] [INTERVAL]
       python tools/check_excursion_v2.py BTCUSDT,ETHUSDT 1h
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.analysis.volatility import build_table  # noqa: E402
from src.analysis.volatility.excursion import RISK_LEVELS, excursion_targets  # noqa: E402
from src.data.history import CandleRepository  # noqa: E402
from src.market.timeframe import interval_to_ms  # noqa: E402
from src.validation.excursion_walkforward import (  # noqa: E402
    coverage_at,
    group_rows,
    level_index,
    median,
    pinball_loss,
    utc_year,
    walk_forward_levels,
)

SYMBOLS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["BTCUSDT", "ETHUSDT"]
INTERVAL = sys.argv[2] if len(sys.argv) > 2 else "1h"

HORIZON = 24
MIN_SEGMENT = 400
TRAIN_YEARS = 2
REFIT_DAYS = 90
DAY_MS = 86_400_000

R1_RANGES = {0.50: (0.47, 0.53), 0.80: (0.77, 0.83), 0.95: (0.92, 0.98)}
R2_TOLERANCE = 0.06
R2_MIN_EVENTS = 300
R3_RANGE = (0.90, 0.99)
R3_MIN_EVENTS = 1000
HALF_MS = 1_735_689_600_000          # 2025-01-01 00:00 UTC


def analyse(symbol):

    interval_ms = interval_to_ms(INTERVAL)

    with CandleRepository() as repo:
        segments = [s for s in repo.segments(symbol, INTERVAL) if len(s) >= MIN_SEGMENT]

    table = build_table(segments, horizon=HORIZON)
    excursions = excursion_targets(segments, horizon=HORIZON)

    result = walk_forward_levels(
        table,
        excursions,
        interval_ms,
        horizon=HORIZON,
        min_train_rows=TRAIN_YEARS * 365 * DAY_MS // interval_ms,
        refit_rows=REFIT_DAYS * DAY_MS // interval_ms,
    )

    e = result.excursion
    levels = [level_index(r) for r in result.ranks]
    years = [utc_year(t) for t in result.timestamps]

    pooled = {q: coverage_at(e, result.quantiles[q]) for q in R1_RANGES}
    baseline_cov = {q: coverage_at(e, result.baseline[q]) for q in R1_RANGES}

    by_level = {}
    for k, rows in sorted(group_rows(levels).items()):
        by_level[k] = {
            "events": len(rows),
            "median": median([e[i] for i in rows]),
            **{q: coverage_at([e[i] for i in rows], [result.quantiles[q][i] for i in rows]) for q in (0.80, 0.95)},
        }

    by_year = {}
    for year, rows in sorted(group_rows(years).items()):
        by_year[year] = (len(rows), coverage_at([e[i] for i in rows], [result.quantiles[0.95][i] for i in rows]))

    halves = {}
    for name, rows in (
        ("before 2025", [i for i, t in enumerate(result.timestamps) if t < HALF_MS]),
        ("from 2025", [i for i, t in enumerate(result.timestamps) if t >= HALF_MS]),
    ):
        cells = {}
        for k, members in sorted(group_rows([levels[i] for i in rows]).items()):
            picked = [rows[j] for j in members]
            cells[k] = {
                "events": len(picked),
                **{q: coverage_at([e[i] for i in picked], [result.quantiles[q][i] for i in picked]) for q in (0.80, 0.95)},
            }
        halves[name] = cells

    losses = {
        q: (pinball_loss(e, result.quantiles[q], q), pinball_loss(e, result.baseline[q], q))
        for q in (0.80, 0.95)
    }

    return {
        "rows": len(table),
        "test_rows": len(result),
        "folds": result.folds,
        "pooled": pooled,
        "baseline_cov": baseline_cov,
        "by_level": by_level,
        "by_year": by_year,
        "halves": halves,
        "losses": losses,
    }


def verdicts(r):

    r1 = all(lo <= r["pooled"][q] <= hi for q, (lo, hi) in R1_RANGES.items())

    tested = {k: v for k, v in r["by_level"].items() if v["events"] >= R2_MIN_EVENTS}
    r2 = len(tested) >= 1 and all(abs(v[q] - q) <= R2_TOLERANCE for v in tested.values() for q in (0.80, 0.95))

    years = {y: v for y, v in r["by_year"].items() if v[0] >= R3_MIN_EVENTS}
    r3 = len(years) >= 1 and all(R3_RANGE[0] <= c <= R3_RANGE[1] for _, c in years.values())

    medians = [r["by_level"][k]["median"] for k in sorted(r["by_level"])]
    r4 = len(medians) == len(RISK_LEVELS) and all(b > a for a, b in zip(medians, medians[1:]))

    r5 = all(model < base for model, base in r["losses"].values())

    r6 = True
    for cells in r["halves"].values():
        tested_half = {k: v for k, v in cells.items() if v["events"] >= R2_MIN_EVENTS}
        r6 = r6 and len(tested_half) >= 1 and all(
            abs(v[q] - q) <= R2_TOLERANCE for v in tested_half.values() for q in (0.80, 0.95)
        )

    return r1, r2, r3, r4, r5, r6


def main():

    print(f"{','.join(SYMBOLS)} {INTERVAL}: walk-forward, train >= {TRAIN_YEARS}y, refit every {REFIT_DAYS}d, horizon {HORIZON}")
    print("E = largest move from the next open, either direction, within the next 24 candles; quantiles q50/q80/q95")
    print()

    reports = {}

    for symbol in SYMBOLS:
        started = time.time()
        reports[symbol] = analyse(symbol)
        print(f"{symbol}: done in {time.time() - started:.0f}s")

    labels = ("R1 pooled coverage", "R2 by risk level", "R3 by year", "R4 level monotone", "R5 beats baseline", "R6 both halves")
    all_ok = [True] * 6

    for symbol in SYMBOLS:

        r = reports[symbol]
        checks = verdicts(r)

        print()
        print("=" * 70)
        print(f"{symbol}: {r['rows']} rows, {r['test_rows']} out-of-sample rows in {r['folds']} folds")
        print("  pooled coverage (model | baseline B):")
        for q, (lo, hi) in R1_RANGES.items():
            print(f"    q{int(q * 100)}: {r['pooled'][q] * 100:5.1f}% | {r['baseline_cov'][q] * 100:5.1f}%   (needs {lo * 100:.0f}-{hi * 100:.0f}%)")
        print("  by risk level (events, median E in bp, q80 coverage, q95 coverage):")
        for k, v in sorted(r["by_level"].items()):
            print(f"    {RISK_LEVELS[k]:<8} {v['events']:>6}  {v['median'] * 10000:7.1f}  {v[0.80] * 100:5.1f}%  {v[0.95] * 100:5.1f}%")
        print(f"  q95 coverage by year (needs {R3_RANGE[0] * 100:.0f}-{R3_RANGE[1] * 100:.0f}% when >= {R3_MIN_EVENTS} events):")
        for year, (count, cov) in r["by_year"].items():
            print(f"    {year}: {count:>6} events  {cov * 100:5.1f}%")
        print("  by half and risk level (events, q80 coverage, q95 coverage):")
        for name, cells in r["halves"].items():
            for k, v in sorted(cells.items()):
                print(f"    {name:<12} {RISK_LEVELS[k]:<8} {v['events']:>6}  {v[0.80] * 100:5.1f}%  {v[0.95] * 100:5.1f}%")
        print("  pinball loss in bp (model vs baseline B):")
        for q, (model, base) in r["losses"].items():
            print(f"    q{int(q * 100)}: {model * 10000:.3f} vs {base * 10000:.3f} -> {'model' if model < base else 'baseline'}")
        print("  " + " | ".join(f"{lab}: {'ok' if ok else 'NO'}" for lab, ok in zip(labels, checks)))

        all_ok = [a and c for a, c in zip(all_ok, checks)]

    print()
    print("=" * 70)
    print("SUMMARY (all assets must pass): " + " | ".join(f"{lab}: {'ok' if ok else 'NO'}" for lab, ok in zip(labels, all_ok)))

    if all(all_ok):
        print("RESULT F-007: the per-level risk sheet is calibrated on this data; forward data is still needed before real use.")
    else:
        print("RESULT F-007: NOT validated; the failed criteria above say what is wrong.")

    print("DONE")


main()
