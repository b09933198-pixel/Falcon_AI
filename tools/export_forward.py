"""
Falcon AI - F-008: export the sheet log to CSV files in the repository

Usage: python tools/export_forward.py [SYMBOLS]

Writes research/forward/sheets_<SYMBOL>_1h.csv from data/history/forward.db. Commit and
push the files after every daily run: the git history is the independent timestamp of
every published sheet.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from config.settings import HISTORY_DB_PATH  # noqa: E402
from src.forward import ForwardStore  # noqa: E402
from src.forward.export import sheets_csv  # noqa: E402

SYMBOLS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["BTCUSDT", "ETHUSDT"]
INTERVAL = "1h"
FORWARD_DB_PATH = HISTORY_DB_PATH.parent / "forward.db"
OUT_DIR = os.path.join(ROOT, "research", "forward")


def main():

    if not FORWARD_DB_PATH.exists():
        sys.exit(f"forward database not found: {FORWARD_DB_PATH}")

    os.makedirs(OUT_DIR, exist_ok=True)

    with ForwardStore(FORWARD_DB_PATH) as store:

        for symbol in SYMBOLS:

            rows = store.sheets(symbol, INTERVAL)
            path = os.path.join(OUT_DIR, f"sheets_{symbol}_{INTERVAL}.csv")

            with open(path, "w", encoding="utf-8", newline="") as handle:
                handle.write(sheets_csv(symbol, INTERVAL, rows))

            done = sum(1 for r in rows if r["outcome"] is not None)
            void = sum(1 for r in rows if r["void"])
            print(f"{symbol}: {len(rows)} sheets ({done} with outcome, {void} void) -> {path}")


main()
