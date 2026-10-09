"""Falcon AI - run every stored candle through the real domain Candle (read-only)."""

import os
import sqlite3
import sys
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.domain.models.candle import Candle  # noqa: E402

DB_PATH = os.path.join(ROOT, "data", "history", "history.db")
QUERY = (
    "SELECT open_time, open, high, low, close, volume, quote_volume, trades, "
    "buy_volume, buy_quote_volume FROM candles "
    "WHERE symbol=? AND interval=? ORDER BY open_time"
)


def main():
    db = sqlite3.connect(DB_PATH)
    series = db.execute(
        "SELECT DISTINCT symbol, interval FROM candles ORDER BY symbol, interval"
    ).fetchall()

    for symbol, interval in series:
        total = invalid = zero_volume = 0
        reasons = Counter()
        examples = {}

        for row in db.execute(QUERY, (symbol, interval)):
            total += 1
            if row[5] == 0:
                zero_volume += 1
            try:
                Candle(
                    timestamp=int(row[0]),
                    open=row[1], high=row[2], low=row[3], close=row[4],
                    volume=row[5], quote_volume=row[6], trades=int(row[7]),
                    buy_volume=row[8], buy_quote_volume=row[9],
                )
            except Exception as exc:
                invalid += 1
                key = f"{type(exc).__name__}: {str(exc)[:70]}"
                reasons[key] += 1
                examples.setdefault(key, row)

        print(f"{symbol} {interval}: total={total} invalid={invalid} zero_volume={zero_volume}")
        for key, count in reasons.most_common(5):
            print(f"    {count} x {key}")
            print(f"       example: {examples[key]}")

    print("DONE")


main()
