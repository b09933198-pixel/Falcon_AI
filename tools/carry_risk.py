"""F-013 exploratory diagnostic (NOT a registered criterion, run after the F-013 verdict).

For every trade in research/results/f013_trades.csv: the highest rise of the spot price from the entry
to the exit. A short perpetual leg collateralised 1:1 is liquidated at a rise of roughly 90-100%.
"""

import csv
import os
import sys
from bisect import bisect_left
from datetime import datetime, timezone

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")
sys.path.insert(0, ROOT)

from src.data.history import CandleRepository  # noqa: E402
from src.lab.carry_risk import max_rise, summarize  # noqa: E402

DBS = [os.path.join(ROOT, "data", "history", "history_old.db"), os.path.join(ROOT, "data", "history", "history.db")]
TRADES = os.path.join(ROOT, "research", "results", "f013_trades.csv")
OUT = os.path.join(ROOT, "research", "results", "f013_risk_exploratory.txt")


def parse(text):
    return int(datetime.strptime(text, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp() * 1000)


def pct(value):
    return f"{value * 100:6.1f}%"


def line(label, s):
    if s["n"] == 0:
        return f"{label:10s} no trades with price data"
    return (f"{label:10s} n={s['n']:4d}  median {pct(s['median'])}  p90 {pct(s['p90'])}  max {pct(s['max'])}  "
            f">=30%: {s['share_ge_30'] * 100:4.1f}%  >=50%: {s['share_ge_50'] * 100:4.1f}%  >=90%: {s['share_ge_90'] * 100:4.1f}%")


def main():
    with open(TRADES, encoding="utf-8") as handle:
        trades = list(csv.DictReader(handle))

    repos = [CandleRepository(p) for p in DBS if os.path.exists(p)]
    cache = {}

    def series(symbol):
        if symbol not in cache:
            merged = {}
            for repo in repos:
                for c in repo.get_candles(symbol, "1h"):
                    merged[c.timestamp] = c
            candles = [merged[k] for k in sorted(merged)]
            cache[symbol] = (candles, [c.timestamp for c in candles])
        return cache[symbol]

    rows, skipped = [], 0
    for t in trades:
        entry, exit_ = parse(t["entry_utc"]), parse(t["exit_utc"])
        candles, stamps = series(t["symbol"])
        window = candles[bisect_left(stamps, entry):bisect_left(stamps, exit_)]
        rise = max_rise(window, entry, exit_)
        if rise is None:
            skipped += 1
            continue
        rows.append((t["symbol"], t["entry_utc"], int(t["entry_utc"][:4]), rise, float(t["net_return_on_capital_pct"])))

    out = ["EXPLORATORY diagnostic, run after the F-013 verdict; not a registered criterion.",
           "Rise = highest spot high between entry and exit divided by the entry open, minus 1 (loss of the short leg per unit of N).",
           "A short collateralised 1:1 is liquidated at a rise of roughly 90-100%; spot is used as a stand-in for the perpetual.",
           f"trades in the file: {len(trades)}, with price data: {len(rows)}, skipped (no spot data at the entry): {skipped}", ""]

    out.append(line("ALL", summarize([r[3] for r in rows])))
    out += ["", "by calendar year of the entry:"]
    for year in sorted({r[2] for r in rows}):
        out.append(line(str(year), summarize([r[3] for r in rows if r[2] == year])))
    out += ["", "by symbol:"]
    for symbol in sorted({r[0] for r in rows}):
        out.append(line(symbol[:-4], summarize([r[3] for r in rows if r[0] == symbol])))
    out += ["", "the 12 largest rises (symbol, entry, rise, net return on capital of the trade):"]
    for r in sorted(rows, key=lambda x: -x[3])[:12]:
        out.append(f"  {r[0]:9s} {r[1]}  rise {pct(r[3])}  trade return {r[4]:+.2f}%")

    text = "\n".join(out)
    with open(OUT, "w", encoding="utf-8") as handle:
        handle.write(text + "\n")
    print(text)


if __name__ == "__main__":
    main()
