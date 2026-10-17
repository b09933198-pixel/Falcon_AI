"""
Falcon AI - F-008 report: status and (when due) evaluation of the forward test

Usage: python tools/forward_report.py [SYMBOLS]

Reads data/history/forward.db plus the archive history. Writes nothing, trades nothing.
Before 120 days AND 2000 completed sheets per asset the output is descriptive only.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from config.settings import HISTORY_DB_PATH  # noqa: E402
from src.data.history import CandleRepository  # noqa: E402
from src.forward import ForwardStore  # noqa: E402
from src.forward.report import asset_stats, render  # noqa: E402
from src.forward.runner import merge_sources  # noqa: E402
from src.market.timeframe import interval_to_ms  # noqa: E402

SYMBOLS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["BTCUSDT", "ETHUSDT"]
INTERVAL = "1h"
FORWARD_DB_PATH = HISTORY_DB_PATH.parent / "forward.db"


def main():

    if not FORWARD_DB_PATH.exists():
        sys.exit(f"forward database not found: {FORWARD_DB_PATH}")

    interval_ms = interval_to_ms(INTERVAL)
    stats = {}

    with CandleRepository() as repo, ForwardStore(FORWARD_DB_PATH) as store:

        for symbol in SYMBOLS:
            archive = [c for segment in repo.segments(symbol, INTERVAL) for c in segment]
            candles = merge_sources(archive, store.candles(symbol, INTERVAL))
            stats[symbol] = asset_stats(store.sheets(symbol, INTERVAL), candles, interval_ms)

    print(render(stats))


main()
