"""
Falcon AI

Forward Layer

Forward store: completed exchange candles, published sheets and their outcomes

Version: 1.0.0

Integrity rules (pre-registered in research/FINDINGS.md, F-008)
---------------------------------------------------------------
  - Candles are never overwritten. A different value for an existing candle is
    counted as a mismatch and the stored value is kept.
  - A sheet is accepted only while its outcome is still unknown: when every candle of
    its outcome window is already closed, the sheet is refused as late.
  - A sheet is written once. It is never edited; only its outcome is filled in later.
  - An outcome window with a missing candle makes the sheet void; nothing is repaired.
"""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from src.domain.models import Candle

SCHEMA = """
CREATE TABLE IF NOT EXISTS candles (
    symbol TEXT NOT NULL, interval TEXT NOT NULL, open_time INTEGER NOT NULL,
    open REAL, high REAL, low REAL, close REAL,
    volume REAL, quote_volume REAL, trades INTEGER, buy_volume REAL, buy_quote_volume REAL,
    fetched_ms INTEGER NOT NULL,
    PRIMARY KEY (symbol, interval, open_time)
);
CREATE TABLE IF NOT EXISTS sheets (
    symbol TEXT NOT NULL, interval TEXT NOT NULL, decision_open_ms INTEGER NOT NULL,
    created_ms INTEGER NOT NULL, model_id TEXT NOT NULL,
    expected REAL NOT NULL, q50 REAL NOT NULL, q80 REAL NOT NULL, q95 REAL NOT NULL,
    rank REAL NOT NULL, level TEXT NOT NULL,
    outcome REAL, outcome_ms INTEGER, void INTEGER NOT NULL DEFAULT 0,
    PRIMARY KEY (symbol, interval, decision_open_ms)
);
CREATE TABLE IF NOT EXISTS models (
    model_id TEXT PRIMARY KEY, symbol TEXT NOT NULL, interval TEXT NOT NULL,
    fit_ms INTEGER NOT NULL, cutoff_ms INTEGER NOT NULL, payload TEXT NOT NULL
);
"""

_CANDLE_COLUMNS = "open_time, open, high, low, close, volume, quote_volume, trades, buy_volume, buy_quote_volume"


class ForwardError(Exception):
    pass


def resolve_outcome(
    candles_by_open: Dict[int, Candle],
    decision_open_ms: int,
    interval_ms: int,
    horizon: int,
    last_closed_open_ms: int,
) -> Tuple[str, Optional[float]]:
    """('ok', E) | ('wait', None) | ('void', None) for one sheet.

    E is measured exactly as in the backtest: from the open of the first candle after
    the decision candle, the larger move in either direction over `horizon` candles.
    """

    first = decision_open_ms + interval_ms
    last = decision_open_ms + horizon * interval_ms

    if last_closed_open_ms < last:
        return "wait", None

    window = []

    for k in range(1, horizon + 1):
        candle = candles_by_open.get(decision_open_ms + k * interval_ms)

        if candle is None:
            return "void", None

        window.append(candle)

    entry = window[0].open
    high = max(c.high for c in window)
    low = min(c.low for c in window)

    return "ok", max(high - entry, entry - low) / entry


class ForwardStore:

    def __init__(self, path):

        path = Path(path)

        if str(path) != ":memory:":
            path.parent.mkdir(parents=True, exist_ok=True)

        self._conn = sqlite3.connect(str(path))
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "ForwardStore":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Candles
    # ------------------------------------------------------------------

    def add_candles(self, symbol: str, interval: str, candles: Sequence[Candle], fetched_ms: int) -> Tuple[int, int]:
        """(new rows, mismatches). Existing candles are kept as they are."""

        new = mismatches = 0

        for c in candles:

            row = (c.open, c.high, c.low, c.close, c.volume, c.quote_volume, c.trades, c.buy_volume, c.buy_quote_volume)
            existing = self._conn.execute(
                "SELECT open, high, low, close, volume, quote_volume, trades, buy_volume, buy_quote_volume "
                "FROM candles WHERE symbol=? AND interval=? AND open_time=?",
                (symbol, interval, c.timestamp),
            ).fetchone()

            if existing is None:
                self._conn.execute(
                    "INSERT INTO candles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (symbol, interval, c.timestamp) + row + (fetched_ms,),
                )
                new += 1
            elif tuple(existing) != row:
                mismatches += 1

        self._conn.commit()

        return new, mismatches

    def candles(self, symbol: str, interval: str) -> List[Candle]:

        rows = self._conn.execute(
            f"SELECT {_CANDLE_COLUMNS} FROM candles WHERE symbol=? AND interval=? ORDER BY open_time",
            (symbol, interval),
        ).fetchall()

        return [
            Candle(timestamp=int(r[0]), open=r[1], high=r[2], low=r[3], close=r[4], volume=r[5],
                   quote_volume=r[6], trades=int(r[7]), buy_volume=r[8], buy_quote_volume=r[9])
            for r in rows
        ]

    # ------------------------------------------------------------------
    # Models
    # ------------------------------------------------------------------

    def save_model(self, model_id: str, symbol: str, interval: str, fit_ms: int, cutoff_ms: int, payload: str) -> None:

        self._conn.execute(
            "INSERT INTO models VALUES (?,?,?,?,?,?)", (model_id, symbol, interval, fit_ms, cutoff_ms, payload)
        )
        self._conn.commit()

    def latest_model(self, symbol: str, interval: str) -> Optional[Tuple[str, int, int, str]]:
        """(model_id, fit_ms, cutoff_ms, payload) of the newest model, or None."""

        row = self._conn.execute(
            "SELECT model_id, fit_ms, cutoff_ms, payload FROM models WHERE symbol=? AND interval=? "
            "ORDER BY fit_ms DESC LIMIT 1",
            (symbol, interval),
        ).fetchone()

        return tuple(row) if row else None

    # ------------------------------------------------------------------
    # Sheets
    # ------------------------------------------------------------------

    def add_sheet(
        self,
        symbol: str,
        interval: str,
        decision_open_ms: int,
        created_ms: int,
        model_id: str,
        expected: float,
        q50: float,
        q80: float,
        q95: float,
        rank: float,
        level: str,
        interval_ms: int,
        horizon: int,
        last_closed_open_ms: int,
    ) -> str:
        """'added' | 'duplicate' | 'late'. A late sheet (outcome already knowable) is never stored."""

        if last_closed_open_ms >= decision_open_ms + horizon * interval_ms:
            return "late"

        exists = self._conn.execute(
            "SELECT 1 FROM sheets WHERE symbol=? AND interval=? AND decision_open_ms=?",
            (symbol, interval, decision_open_ms),
        ).fetchone()

        if exists:
            return "duplicate"

        self._conn.execute(
            "INSERT INTO sheets (symbol, interval, decision_open_ms, created_ms, model_id, expected, q50, q80, q95, rank, level) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (symbol, interval, decision_open_ms, created_ms, model_id, expected, q50, q80, q95, rank, level),
        )
        self._conn.commit()

        return "added"

    def pending(self, symbol: str, interval: str) -> List[int]:
        """Decision open times of sheets whose outcome is still open."""

        rows = self._conn.execute(
            "SELECT decision_open_ms FROM sheets WHERE symbol=? AND interval=? AND outcome IS NULL AND void=0 "
            "ORDER BY decision_open_ms",
            (symbol, interval),
        ).fetchall()

        return [int(r[0]) for r in rows]

    def set_outcome(self, symbol: str, interval: str, decision_open_ms: int, outcome: float, outcome_ms: int) -> None:

        self._conn.execute(
            "UPDATE sheets SET outcome=?, outcome_ms=? WHERE symbol=? AND interval=? AND decision_open_ms=? "
            "AND outcome IS NULL AND void=0",
            (outcome, outcome_ms, symbol, interval, decision_open_ms),
        )
        self._conn.commit()

    def set_void(self, symbol: str, interval: str, decision_open_ms: int) -> None:

        self._conn.execute(
            "UPDATE sheets SET void=1 WHERE symbol=? AND interval=? AND decision_open_ms=? AND outcome IS NULL",
            (symbol, interval, decision_open_ms),
        )
        self._conn.commit()

    def sheets(self, symbol: str, interval: str) -> List[Dict]:

        cursor = self._conn.execute(
            "SELECT decision_open_ms, created_ms, model_id, expected, q50, q80, q95, rank, level, outcome, outcome_ms, void "
            "FROM sheets WHERE symbol=? AND interval=? ORDER BY decision_open_ms",
            (symbol, interval),
        )
        names = [d[0] for d in cursor.description]

        return [dict(zip(names, row)) for row in cursor.fetchall()]
