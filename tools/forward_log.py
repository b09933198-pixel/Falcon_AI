"""
Falcon AI - F-008 daily run: fetch Toobit candles, publish risk sheets, resolve outcomes

Usage: python tools/forward_log.py [SYMBOLS]
       python tools/forward_log.py BTCUSDT,ETHUSDT

Reads the archive history (data/history/history.db), stores fresh COMPLETED Toobit
candles in data/history/forward.db, publishes one sheet for each of the last 24 closes
and fills in the outcomes of older sheets. It trades nothing and sends nothing.
Run it at least once every ~50 days (it fetches the last 1500 candles each time), and
preferably every day.
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from config.settings import HISTORY_DB_PATH  # noqa: E402
from src.data.history import CandleRepository  # noqa: E402
from src.data.toobit import ToobitError, fetch_recent  # noqa: E402
from src.forward import ForwardStore  # noqa: E402
from src.forward.format import format_sheet_fa  # noqa: E402
from src.forward.runner import run_symbol, utc_stamp  # noqa: E402
from src.market.timeframe import interval_to_ms  # noqa: E402

SYMBOLS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["BTCUSDT", "ETHUSDT"]
INTERVAL = "1h"
FETCH_COUNT = 1500
FORWARD_DB_PATH = HISTORY_DB_PATH.parent / "forward.db"


def main():

    interval_ms = interval_to_ms(INTERVAL)
    now_ms = int(time.time() * 1000)
    print(f"forward run at {utc_stamp(now_ms)} UTC, symbols {','.join(SYMBOLS)}, db {FORWARD_DB_PATH}")

    with CandleRepository() as repo, ForwardStore(FORWARD_DB_PATH) as store:

        for symbol in SYMBOLS:

            print()
            print("=" * 70)
            archive = [c for segment in repo.segments(symbol, INTERVAL) for c in segment]

            def fetch():
                return fetch_recent(symbol, INTERVAL, interval_ms, FETCH_COUNT, now_ms)

            try:
                s = run_symbol(store, symbol, archive, fetch, now_ms, INTERVAL, interval_ms)
            except ToobitError as exc:
                print(f"{symbol}: exchange problem, nothing written for this symbol: {exc}")
                continue

            print(f"{symbol}: candles +{s.new_candles} (mismatches {s.mismatches}), newest closed candle {utc_stamp(s.last_closed_open_ms)} UTC")
            print(f"  model {s.model_id}{' (refitted now)' if s.refit else ''}")
            print(f"  sheets: added {s.added}, already there {s.duplicates}, refused late {s.late}, no history {s.no_history}")
            print(f"  outcomes: filled {s.outcomes_ok}, void {s.outcomes_void}, still open {s.pending}")

            for warning in s.warnings:
                print(f"  WARNING: {warning}")

            if s.latest_sheet is not None:
                print()
                print(format_sheet_fa(symbol, INTERVAL, s.latest_sheet, s.latest_close, interval_ms))

    print()
    print("DONE")


main()
