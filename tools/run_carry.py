"""Funding-rate carry test (F-013), one look.

  python tools/run_carry.py --config config/carry_f013.json --registration F-013

Refuses to run on uncommitted changes, without the registration in research/FINDINGS.md, or when the
result file already exists (a second look needs a new registration).
"""

import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from src.data.derivatives import DerivativesStore  # noqa: E402
from src.lab.carry import (CarryParams, DAY_MS, annual_return, by_year, judge, simulate_carry,  # noqa: E402
                           trade_returns)

NOT_MODELLED = (
    "Not modelled (so not tested): spot / perpetual price difference at entry, exit and in between; liquidation of the "
    "short leg in a sharp rally; transfer and borrowing costs; exchange risk of two venues; taxes; whether spot and "
    "perpetual of every symbol trade on one venue at these costs. A pass is a statement about funding income only."
)


def git_head():
    try:
        return subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=ROOT, text=True).strip()
    except Exception:
        return "unknown"


def tree_is_clean():
    try:
        out = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL)
    except Exception:
        return True
    return out.strip() == ""


def utc(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def load_funding(symbols):
    out = {}
    with DerivativesStore() as store:
        for symbol in symbols:
            rows = sorted(set((r[0], r[2]) for r in store.funding(symbol)))
            out[symbol] = ([r[0] for r in rows], [r[1] for r in rows])
    return out


def render(config, params, per_symbol, trades, verdict, commit):
    lines = [
        f"F-013 funding carry, code commit {commit}",
        f"costs: round trip {params.round_trip_cost * 100:.2f}% of N, capital = {params.capital_factor:.1f} x N, "
        f"entry D{params.entry_window_days:g} >= {params.entry_daily_rate:.5f}/day, "
        f"exit D{params.exit_window_days:g} <= {params.exit_daily_rate:.5f}/day, max hold {params.max_hold_days:g} days",
        "",
        "symbol     events  first .. last                      trades  days   time%  annual%  mean funding/trade%",
    ]

    for symbol, info in per_symbol.items():
        if info is None:
            lines.append(f"{symbol:10s} NO FUNDING DATA")
            continue
        n, first, last, tr = info
        days = sum((t.exit_ms - t.entry_ms) / DAY_MS for t in tr)
        span = max((last - first) / DAY_MS, 1e-9)
        mean_f = sum(t.funding for t in tr) / len(tr) * 100 if tr else 0.0
        ann = annual_return(tr, params) * 100 if tr else 0.0
        lines.append(f"{symbol:10s} {n:6d}  {utc(first)} .. {utc(last)}  {len(tr):6d} {days:5.0f} {days / span * 100:6.1f} "
                     f"{ann:+8.2f}  {mean_f:+.3f}")

    lines += ["", "by calendar year of the exit (trades, pooled net return on capital):"]

    for year, (n, total) in sorted(by_year(trades, params).items()):
        lines.append(f"  {year}: {n:4d} trades  {total * 100:+.2f}%")

    reasons = {}
    for t in trades:
        reasons[t.reason] = reasons.get(t.reason, 0) + 1
    lines.append("exit reasons: " + ", ".join(f"{k} {v}" for k, v in sorted(reasons.items())))
    returns = trade_returns(trades, params)
    if returns:
        lines.append(f"all trades: {len(trades)}, mean net return on capital per trade {sum(returns) / len(returns) * 100:+.3f}%, "
                     f"worst {min(returns) * 100:+.2f}%, best {max(returns) * 100:+.2f}%")

    lines += ["", "REGISTERED CONDITIONS"]
    for text, value, ok in verdict["checks"]:
        lines.append(f"  {'PASS' if ok else 'FAIL'}  {text}: {value}")
    lines += ["", "RESULT: " + ("PASSED all five conditions" if verdict["passed"] else "FAILED (not all five conditions hold)"),
              "", NOT_MODELLED]

    return "\n".join(lines)


def trades_csv(trades, params):
    lines = ["symbol,entry_utc,exit_utc,days,funding_pct_of_N,net_return_on_capital_pct,reason"]
    for t, r in zip(trades, trade_returns(trades, params)):
        lines.append(f"{t.symbol},{utc(t.entry_ms)},{utc(t.exit_ms)},{(t.exit_ms - t.entry_ms) / DAY_MS:.2f},"
                     f"{t.funding * 100:.4f},{r * 100:.4f},{t.reason}")
    return "\n".join(lines) + "\n"


def main(argv=None, funding=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=os.path.join(ROOT, "config", "carry_f013.json"))
    ap.add_argument("--registration", required=True)
    ap.add_argument("--out-dir", default=os.path.join(ROOT, "research", "results"))
    args = ap.parse_args(argv)

    with open(args.config, encoding="utf-8") as handle:
        config = json.load(handle)

    findings = open(os.path.join(ROOT, "research", "FINDINGS.md"), encoding="utf-8").read()
    if f"### {args.registration} pre-registration" not in findings:
        sys.exit(f"refused: no pre-registration section for {args.registration} in research/FINDINGS.md")
    if not tree_is_clean():
        sys.exit("refused: uncommitted changes; commit the code and the config first")

    tag = args.registration.lower().replace("-", "")
    txt = os.path.join(args.out_dir, f"{tag}_carry.txt")
    if os.path.exists(txt):
        sys.exit(f"refused: the result already exists ({txt}); a second look needs a new registration")

    params = CarryParams(config["entry_window_days"], config["entry_daily_rate"], config["exit_window_days"],
                         config["exit_daily_rate"], config["max_hold_days"], config["round_trip_cost"],
                         config["capital_factor"])
    data = funding if funding is not None else load_funding(config["symbols"])

    per_symbol, trades = {}, []
    for symbol in config["symbols"]:
        times, rates = data.get(symbol, ([], []))
        if len(times) < 2:
            per_symbol[symbol] = None
            continue
        tr = simulate_carry(symbol, times, rates, params)
        per_symbol[symbol] = (len(times), times[0], times[-1], tr)
        trades += tr

    verdict = judge(trades, params, config)
    text = render(config, params, per_symbol, trades, verdict, git_head())

    os.makedirs(args.out_dir, exist_ok=True)
    with open(txt, "x", encoding="utf-8") as handle:
        handle.write(text + "\n")
    with open(os.path.join(args.out_dir, f"{tag}_trades.csv"), "x", encoding="utf-8") as handle:
        handle.write(trades_csv(trades, params))
    print(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
