"""
Falcon AI

Data Layer

Derivatives data (Binance USDT-M futures archives)

Version: 1.0.0

Funding rates and "metrics" (open interest, long/short ratios, taker buy/sell
volume ratio, one row per 5 minutes) from data.binance.vision, stored in its
own SQLite file so the candle history stays untouched.

Time conventions
----------------
Every timestamp is UTC milliseconds.
  funding   calc_time of the funding event (8-hourly); the rate is known from then on.
  metrics   create_time of the 5-minute row. The archive does not say whether it
            marks the start or the end of the period, so research code must treat
            a row as available only AFTER create_time + 5 minutes.

Rows inside an archive file are NOT in time order; the database key sorts them.

Standard library only.
"""

from __future__ import annotations

import csv
import io
import sqlite3
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional, Sequence, Tuple

from config.settings import HISTORY_DB_PATH

DERIVATIVES_DB_PATH = Path(HISTORY_DB_PATH).parent / "derivatives.db"
BASE_URL = "https://data.binance.vision/data/futures/um"

FUNDING_HEADER = ["calc_time", "funding_interval_hours", "last_funding_rate"]
METRICS_HEADER = [
    "create_time",
    "symbol",
    "sum_open_interest",
    "sum_open_interest_value",
    "count_toptrader_long_short_ratio",
    "sum_toptrader_long_short_ratio",
    "count_long_short_ratio",
    "sum_taker_long_short_vol_ratio",
]

MAX_ZIP_BYTES = 5_000_000
MAX_CSV_BYTES = 20_000_000


class DerivativesError(Exception):
    pass


# ----------------------------------------------------------------------
# Parsing
# ----------------------------------------------------------------------

def utc_ms(text: str) -> int:
    """'YYYY-MM-DD HH:MM:SS' (UTC) -> milliseconds since the epoch."""

    try:
        moment = datetime.strptime(text.strip(), "%Y-%m-%d %H:%M:%S")
    except ValueError as error:
        raise DerivativesError(f"bad timestamp: {text!r}") from error

    return int(moment.replace(tzinfo=timezone.utc).timestamp() * 1000)


def _number(text: str) -> Optional[float]:

    text = text.strip()

    if text == "":
        return None

    try:
        value = float(text)
    except ValueError as error:
        raise DerivativesError(f"bad number: {text!r}") from error

    if value != value or value in (float("inf"), float("-inf")):
        raise DerivativesError(f"non-finite number: {text!r}")

    return value


def parse_funding(rows: Sequence[Sequence[str]]) -> List[Tuple[int, int, float]]:
    """[(calc_time_ms, interval_hours, rate)] in file order."""

    if not rows or list(rows[0]) != FUNDING_HEADER:
        raise DerivativesError("unexpected funding header")

    out: List[Tuple[int, int, float]] = []

    for row in rows[1:]:

        if len(row) != 3:
            raise DerivativesError(f"funding row has {len(row)} fields")

        try:
            stamp, interval = int(row[0]), int(row[1])
        except ValueError as error:
            raise DerivativesError(f"bad funding row: {list(row)}") from error

        rate = _number(row[2])

        if rate is None or stamp < 0 or interval < 1:
            raise DerivativesError(f"bad funding row: {list(row)}")

        out.append((stamp, interval, rate))

    return out


def parse_metrics(rows: Sequence[Sequence[str]], symbol: str) -> List[tuple]:
    """[(ts_ms, oi, oi_value, top_count_ls, top_sum_ls, count_ls, taker_ls)] in file order."""

    if not rows or list(rows[0]) != METRICS_HEADER:
        raise DerivativesError("unexpected metrics header")

    out: List[tuple] = []

    for row in rows[1:]:

        if len(row) != len(METRICS_HEADER):
            raise DerivativesError(f"metrics row has {len(row)} fields")

        if row[1] != symbol:
            raise DerivativesError(f"row for {row[1]!r} inside a {symbol} file")

        out.append((utc_ms(row[0]),) + tuple(_number(v) for v in row[2:]))

    return out


# ----------------------------------------------------------------------
# Download
# ----------------------------------------------------------------------

def funding_url(symbol: str, tag: str) -> str:
    return f"{BASE_URL}/monthly/fundingRate/{symbol}/{symbol}-fundingRate-{tag}.zip"


def metrics_url(symbol: str, tag: str) -> str:
    return f"{BASE_URL}/daily/metrics/{symbol}/{symbol}-metrics-{tag}.zip"


def fetch_zip_csv(url: str, timeout: int = 30) -> Optional[List[List[str]]]:
    """Rows of the single CSV inside a zip, or None when the file does not exist (404)."""

    try:
        with urllib.request.urlopen(url, timeout=timeout) as response:
            data = response.read(MAX_ZIP_BYTES + 1)
    except urllib.error.HTTPError as error:
        if error.code == 404:
            return None
        raise

    if len(data) > MAX_ZIP_BYTES:
        raise DerivativesError("archive is unexpectedly large")

    with zipfile.ZipFile(io.BytesIO(data)) as archive:

        infos = [i for i in archive.infolist() if i.filename.lower().endswith(".csv")]

        if len(infos) != 1:
            raise DerivativesError("archive must hold exactly one CSV")

        if infos[0].file_size > MAX_CSV_BYTES:
            raise DerivativesError("CSV is unexpectedly large")

        text = archive.read(infos[0]).decode("utf-8")

    return list(csv.reader(io.StringIO(text)))


# ----------------------------------------------------------------------
# Storage
# ----------------------------------------------------------------------

_SCHEMA = """
CREATE TABLE IF NOT EXISTS funding (
    symbol TEXT NOT NULL, calc_time INTEGER NOT NULL,
    interval_hours INTEGER NOT NULL, rate REAL NOT NULL,
    PRIMARY KEY (symbol, calc_time)
);
CREATE TABLE IF NOT EXISTS metrics (
    symbol TEXT NOT NULL, ts INTEGER NOT NULL,
    open_interest REAL, open_interest_value REAL,
    top_count_ls REAL, top_sum_ls REAL, count_ls REAL, taker_ls_vol REAL,
    PRIMARY KEY (symbol, ts)
);
CREATE TABLE IF NOT EXISTS downloaded (
    kind TEXT NOT NULL, symbol TEXT NOT NULL, tag TEXT NOT NULL, rows INTEGER NOT NULL,
    PRIMARY KEY (kind, symbol, tag)
);
"""


class DerivativesStore:
    """Writable store; rows are replaced by key, so re-running is safe."""

    def __init__(self, db_path=None):
        path = Path(db_path if db_path is not None else DERIVATIVES_DB_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path))
        self._conn.executescript(_SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.commit()
        self._conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()

    def commit(self) -> None:
        self._conn.commit()

    # download bookkeeping: rows >= 0 stored, -1 = file does not exist
    def done(self, kind: str, symbol: str, tag: str) -> bool:
        cursor = self._conn.execute(
            "SELECT 1 FROM downloaded WHERE kind=? AND symbol=? AND tag=?", (kind, symbol, tag)
        )
        return cursor.fetchone() is not None

    def mark(self, kind: str, symbol: str, tag: str, rows: int) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO downloaded (kind, symbol, tag, rows) VALUES (?,?,?,?)",
            (kind, symbol, tag, rows),
        )

    def add_funding(self, symbol: str, rows: Sequence[Tuple[int, int, float]]) -> None:
        self._conn.executemany(
            "INSERT OR REPLACE INTO funding (symbol, calc_time, interval_hours, rate) VALUES (?,?,?,?)",
            [(symbol,) + tuple(r) for r in rows],
        )

    def add_metrics(self, symbol: str, rows: Sequence[tuple]) -> None:
        self._conn.executemany(
            "INSERT OR REPLACE INTO metrics (symbol, ts, open_interest, open_interest_value, "
            "top_count_ls, top_sum_ls, count_ls, taker_ls_vol) VALUES (?,?,?,?,?,?,?,?)",
            [(symbol,) + tuple(r) for r in rows],
        )

    # reading (always sorted by time)
    def funding(self, symbol: str) -> List[Tuple[int, int, float]]:
        cursor = self._conn.execute(
            "SELECT calc_time, interval_hours, rate FROM funding WHERE symbol=? ORDER BY calc_time",
            (symbol,),
        )
        return cursor.fetchall()

    def metrics(self, symbol: str) -> List[tuple]:
        cursor = self._conn.execute(
            "SELECT ts, open_interest, open_interest_value, top_count_ls, top_sum_ls, count_ls, "
            "taker_ls_vol FROM metrics WHERE symbol=? ORDER BY ts",
            (symbol,),
        )
        return cursor.fetchall()

    def summary(self, symbol: str) -> dict:
        """Coverage numbers for a quick health check."""

        one = self._conn.execute

        metric_rows = one("SELECT COUNT(*), MIN(ts), MAX(ts) FROM metrics WHERE symbol=?", (symbol,)).fetchone()
        funding_rows = one("SELECT COUNT(*), MIN(calc_time), MAX(calc_time) FROM funding WHERE symbol=?", (symbol,)).fetchone()
        off_grid = one("SELECT COUNT(*) FROM metrics WHERE symbol=? AND ts % 300000 != 0", (symbol,)).fetchone()[0]
        per_day = one(
            "SELECT ts / 86400000 AS day, COUNT(*) FROM metrics WHERE symbol=? GROUP BY day", (symbol,)
        ).fetchall()
        intervals = one(
            "SELECT interval_hours, COUNT(*) FROM funding WHERE symbol=? GROUP BY interval_hours", (symbol,)
        ).fetchall()
        missing_files = one(
            "SELECT kind, COUNT(*) FROM downloaded WHERE symbol=? AND rows < 0 GROUP BY kind", (symbol,)
        ).fetchall()

        return {
            "metric_rows": metric_rows[0], "metric_first": metric_rows[1], "metric_last": metric_rows[2],
            "funding_rows": funding_rows[0], "funding_first": funding_rows[1], "funding_last": funding_rows[2],
            "off_grid": off_grid,
            "days": len(per_day),
            "short_days": [(d, n) for d, n in per_day if n != 288],
            "intervals": dict(intervals),
            "missing_files": dict(missing_files),
        }
