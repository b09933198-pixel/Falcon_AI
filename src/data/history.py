"""
Falcon AI

Data Layer

Candle History Repository (read-only)

Reads stored historical candles and returns domain Candle objects.

Conventions:
    - Candle.timestamp is the candle OPEN time in UTC milliseconds.
    - Missing candles are never filled or interpolated.
    - segments() splits history at gaps, so analysis restarts after a gap
      instead of treating the series as continuous.
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Iterator, List, Optional

from config.settings import HISTORY_DB_PATH
from src.domain.models.candle import Candle
from src.market.timeframe import interval_to_ms

_COLUMNS = (
    "open_time, open, high, low, close, volume, quote_volume, "
    "trades, buy_volume, buy_quote_volume"
)


class HistoryError(Exception):
    """Raised when stored history is missing or inconsistent."""


@dataclass(frozen=True)
class Coverage:
    symbol: str
    interval: str
    count: int
    first: Optional[int]
    last: Optional[int]


class CandleRepository:

    def __init__(self, db_path=None):

        path = Path(db_path if db_path is not None else HISTORY_DB_PATH)

        if not path.exists():
            raise HistoryError(f"History database not found: {path}")

        self._conn = sqlite3.connect(str(path))
        self._conn.execute("PRAGMA query_only = ON")

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "CandleRepository":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # ----------------------------------------------------------
    # Queries
    # ----------------------------------------------------------

    def coverage(self, symbol: str, interval: str) -> Coverage:

        interval_to_ms(interval)

        count, first, last = self._conn.execute(
            "SELECT COUNT(*), MIN(open_time), MAX(open_time) "
            "FROM candles WHERE symbol=? AND interval=?",
            (symbol, interval),
        ).fetchone()

        return Coverage(symbol, interval, count, first, last)

    def iter_candles(
        self,
        symbol: str,
        interval: str,
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> Iterator[Candle]:
        """Yield candles in ascending time. start is inclusive, end exclusive."""

        interval_to_ms(interval)

        for row in self._select(symbol, interval, start, end):
            yield self._to_candle(row)

    def get_candles(
        self,
        symbol: str,
        interval: str,
        start: Optional[int] = None,
        end: Optional[int] = None,
        limit: Optional[int] = None,
    ) -> List[Candle]:
        """Return candles in ascending time.

        With limit, returns the most recent `limit` candles of the range.
        """

        interval_to_ms(interval)

        if limit is None:
            return list(self.iter_candles(symbol, interval, start, end))

        if limit <= 0:
            raise ValueError("limit must be positive")

        rows = self._select(
            symbol, interval, start, end, descending=True, limit=limit
        )

        return [self._to_candle(row) for row in reversed(list(rows))]

    def segments(
        self,
        symbol: str,
        interval: str,
        start: Optional[int] = None,
        end: Optional[int] = None,
    ) -> Iterator[List[Candle]]:
        """Yield contiguous runs of candles, split wherever candles are missing."""

        step = interval_to_ms(interval)

        current: List[Candle] = []
        previous: Optional[int] = None

        for candle in self.iter_candles(symbol, interval, start, end):

            if previous is not None:

                delta = candle.timestamp - previous

                if delta < step:
                    raise HistoryError(
                        f"Misaligned candles in {symbol} {interval} "
                        f"at {candle.timestamp}"
                    )

                if delta > step:
                    yield current
                    current = []

            current.append(candle)
            previous = candle.timestamp

        if current:
            yield current

    # ----------------------------------------------------------
    # Internals
    # ----------------------------------------------------------

    def _select(self, symbol, interval, start, end, descending=False, limit=None):

        sql = f"SELECT {_COLUMNS} FROM candles WHERE symbol=? AND interval=?"
        params: list = [symbol, interval]

        if start is not None:
            sql += " AND open_time>=?"
            params.append(int(start))

        if end is not None:
            sql += " AND open_time<?"
            params.append(int(end))

        sql += " ORDER BY open_time " + ("DESC" if descending else "ASC")

        if limit is not None:
            sql += " LIMIT ?"
            params.append(int(limit))

        return self._conn.execute(sql, params)

    @staticmethod
    def _to_candle(row) -> Candle:

        return Candle(
            timestamp=int(row[0]),
            open=row[1],
            high=row[2],
            low=row[3],
            close=row[4],
            volume=row[5],
            quote_volume=row[6],
            trades=int(row[7]),
            buy_volume=row[8],
            buy_quote_volume=row[9],
        )
