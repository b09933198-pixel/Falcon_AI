"""
Falcon AI - F-009 strategy lab

Usage:
  python tools/run_lab.py --check      data coverage and signal counts in the DEVELOPMENT part only (no trades, no results)
  python tools/run_lab.py --holdout    THE ONE LOOK at the hold-out (refuses to run twice per timeframe)

Options: --config PATH (default config/lab.json), --out-dir PATH (default research/results),
         --registration F-0xx (needed for a timeframe that F-009 does not cover; its FINDINGS section must name it).

The timeframes, symbols, costs and the hold-out start come from the config file, not from code.
"""

import argparse
import json
import os
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.analysis.volatility.risksheet import split_contiguous  # noqa: E402
from src.data.derivatives import DerivativesStore  # noqa: E402
from src.data.history import CandleRepository  # noqa: E402
from src.lab.engine import Costs  # noqa: E402
from src.lab.runner import (  # noqa: E402
    Lab, aggregate, check_registered, parse_utc, render, run_all, timeframe_factor, trades_csv, utc,
)
from src.lab.strategies import NAMES, STRATEGIES  # noqa: E402
from src.market.timeframe import interval_to_ms  # noqa: E402
from src.lab.runner import drop_off_grid  # noqa: E402

NOTES = [
    "timeout N = held at most N candles, entry candle included; funding charged for events after the entry open up to the exit candle close",
    "signal skipped when the structural stop is on the wrong side of the entry or a measured-move target is already behind it; trade still open at the end of data is discarded (counts shown per strategy)",
    "win = net R after costs > 0; gate A break-even win rate = (1 + mean cost in R) / 2",
    "squeeze percentile = sorted position int(0.2 x 119) of 120 bandwidths; S05 uses consecutive confirmed pivots; S13 uses the nearest cluster of any kind; trendlines go through pivot wicks",
    "BTC and ETH trades are pooled, trades of different symbols overlap in time, so p-values are somewhat optimistic",
]


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def tree_is_clean():
    """True when git reports no uncommitted change (or git is not available)."""
    try:
        out = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return True
    return out.strip() == ""


def load(config, timeframe):

    factor = timeframe_factor(timeframe, interval_to_ms)
    tf_ms = interval_to_ms(timeframe)
    data = {}

    with CandleRepository(config.get("history_db")) as repo, DerivativesStore() as deriv:
        for symbol in config["symbols"]:
            raw = drop_off_grid(repo.get_candles(symbol, "1h"), 3_600_000)
            if config.get("holdout_end_utc"):
                cut = parse_utc(config["holdout_end_utc"])
                raw = [c for c in raw if c.timestamp < cut]
            merged = []

            for segment in split_contiguous(raw, 3_600_000):
                merged += aggregate(segment, factor)

            funding_rows = deriv.funding(symbol)
            funding = ([r[0] for r in funding_rows], [r[2] for r in funding_rows]) if funding_rows else None
            data[symbol] = (split_contiguous(merged, tf_ms), funding)

    return data, tf_ms


def coverage_lines(data, tf_ms, start_ms):

    lines = []

    for symbol, (segs, funding) in data.items():
        count = sum(len(s) for s in segs)
        first, last = segs[0][0].timestamp, segs[-1][-1].timestamp
        hold = sum(1 for s in segs for c in s if c.timestamp >= start_ms)
        text = f"{symbol}: {count} candles in {len(segs)} segment(s), {utc(first)} .. {utc(last)}, hold-out candles {hold}"

        if funding:
            text += f"; funding {len(funding[0])} events {utc(funding[0][0])} .. {utc(funding[0][-1])}"
        else:
            text += "; NO FUNDING DATA"

        lines.append(text)

    return lines


def main():

    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--holdout", action="store_true")
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "lab.json"))
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "research", "results"))
    ap.add_argument("--registration", default=None)
    args = ap.parse_args()

    if args.check == args.holdout:
        sys.exit("choose exactly one of --check and --holdout")

    with open(args.config, encoding="utf-8") as handle:
        config = json.load(handle)

    if args.holdout and not tree_is_clean():
        sys.exit("refused: uncommitted changes; commit the code and the config first, the hold-out must be run on committed code")

    start_ms = parse_utc(config["holdout_start_utc"])
    costs = Costs(config["taker_fee"], config["slippage"], 1.0)
    findings = open(os.path.join(ROOT, "research", "FINDINGS.md"), encoding="utf-8").read()
    timeframes = config["timeframes"]
    tests = 2 * len(STRATEGIES) * len(timeframes)
    alpha = config["family_alpha"] / tests

    for timeframe in timeframes:
        try:
            reg = check_registered(timeframe, args.registration, findings)
        except ValueError as error:
            sys.exit(f"refused: {error}")

        tag = reg.lower().replace("-", "")
        txt = os.path.join(args.out_dir, f"{tag}_holdout_{timeframe}.txt")

        if args.holdout and os.path.exists(txt):
            sys.exit(f"refused: the hold-out for {timeframe} was already seen ({txt}); a second look needs a new registration")

        data, tf_ms = load(config, timeframe)
        print(f"== {timeframe} (registration {reg}), code {git_head()}")

        for line in coverage_lines(data, tf_ms, start_ms):
            print(line)

        lab = Lab(data, tf_ms, start_ms)

        if args.check:
            print("signals in the DEVELOPMENT part only (counts, no trades, no performance):")
            for name in STRATEGIES:
                print(f"  {name} {NAMES[name]:22s} {lab.signal_counts(name, 'dev')}")
            continue

        results = run_all(lab, costs, alpha, config["min_trades"], config["min_win_rate"])
        end_ms = max(segs[-1][-1].timestamp for segs, _ in data.values()) + tf_ms
        notes = [f"registration {reg}, code commit {git_head()}"] + coverage_lines(data, tf_ms, start_ms) + NOTES

        for symbol, (_, funding) in data.items():
            if not funding or funding[0][0] > start_ms or funding[0][-1] < end_ms - 8 * 3_600_000:
                notes.append(f"WARNING: funding data of {symbol} does not cover the whole hold-out window")

        meta = {"registration": reg, "timeframe": timeframe, "symbols": list(data), "start_ms": start_ms, "end_ms": end_ms,
                "fee": costs.fee, "slippage": costs.slippage, "tests": tests, "alpha": alpha,
                "min_trades": config["min_trades"], "min_win": config["min_win_rate"], "notes": notes}
        text = render(results, meta)
        os.makedirs(args.out_dir, exist_ok=True)

        with open(txt, "x", encoding="utf-8") as handle:
            handle.write(text + "\n")

        with open(os.path.join(args.out_dir, f"{tag}_trades_{timeframe}.csv"), "x", encoding="utf-8") as handle:
            handle.write(trades_csv(results, tf_ms))

        print(text)


main()
