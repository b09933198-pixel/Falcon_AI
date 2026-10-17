"""
Falcon AI

Forward Layer

CSV export of the sheet log (for the repository, so git history timestamps every sheet)

Version: 1.0.0

Floats are written with repr (exact round trip), missing outcomes as empty fields,
rows sorted by decision time. Sheet values never change after they are written; only
the outcome columns fill in later.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Dict, Sequence

COLUMNS = (
    "symbol", "interval", "decision_open_ms", "decision_utc", "created_ms", "created_utc",
    "model_id", "expected", "q50", "q80", "q95", "rank", "level", "outcome", "outcome_ms", "void",
)


def _utc(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def _cell(value) -> str:

    if value is None:
        return ""

    if isinstance(value, float):
        return repr(value)

    return str(value)


def sheets_csv(symbol: str, interval: str, rows: Sequence[Dict]) -> str:
    """The whole sheet log of one symbol as CSV text."""

    out = io.StringIO()
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(COLUMNS)

    for row in sorted(rows, key=lambda r: r["decision_open_ms"]):

        writer.writerow([
            symbol, interval, row["decision_open_ms"], _utc(row["decision_open_ms"]),
            row["created_ms"], _utc(row["created_ms"]), row["model_id"],
            _cell(row["expected"]), _cell(row["q50"]), _cell(row["q80"]), _cell(row["q95"]),
            _cell(row["rank"]), row["level"],
            _cell(row["outcome"]), _cell(row["outcome_ms"]), row["void"],
        ])

    return out.getvalue()
