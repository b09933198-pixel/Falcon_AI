"""Falcon AI - historical candle downloader (stdlib only, resumable).

Source : data.binance.vision (Binance spot monthly archives)
Output : data/history/history.db (SQLite, not committed to git)
Usage  : python tools/download_history.py [SYMBOLS] [INTERVALS]
         python tools/download_history.py BTCUSDT,ETHUSDT 15m,1h,4h,1d
"""

import io
import os
import sqlite3
import sys
import time
import urllib.error
import urllib.request
import zipfile
from datetime import datetime, timezone

BASE = "https://data.binance.vision/data/spot/monthly/klines"
DB_PATH = os.environ.get("FALCON_HISTORY_DB") or os.path.join("data", "history", "history.db")
DEFAULT_SYMBOLS = ["BTCUSDT", "ETHUSDT"]
DEFAULT_INTERVALS = ["15m", "1h", "4h", "1d"]
START = tuple(int(x) for x in os.environ.get("FALCON_HISTORY_START", "2021-01").split("-"))
STEP_MS = {
    "1m": 60000, "5m": 300000, "15m": 900000, "30m": 1800000,
    "1h": 3600000, "2h": 7200000, "4h": 14400000, "1d": 86400000,
}

SCHEMA = """
CREATE TABLE IF NOT EXISTS candles (
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    open_time INTEGER NOT NULL,
    open REAL, high REAL, low REAL, close REAL,
    volume REAL, quote_volume REAL, trades INTEGER,
    buy_volume REAL, buy_quote_volume REAL,
    source TEXT NOT NULL,
    PRIMARY KEY (symbol, interval, open_time)
);
CREATE TABLE IF NOT EXISTS downloaded (
    symbol TEXT NOT NULL,
    interval TEXT NOT NULL,
    month TEXT NOT NULL,
    rows INTEGER NOT NULL,
    PRIMARY KEY (symbol, interval, month)
);
"""


def months():
    now = datetime.now(timezone.utc)
    last = (now.year, now.month - 1) if now.month > 1 else (now.year - 1, 12)
    if os.environ.get("FALCON_HISTORY_END"):
        last = tuple(int(x) for x in os.environ["FALCON_HISTORY_END"].split("-"))
    y, m = START
    while (y, m) <= last:
        yield f"{y:04d}-{m:02d}"
        m += 1
        if m > 12:
            y, m = y + 1, 1


def fetch(url):
    """Return bytes, or None when the file does not exist (404)."""
    for attempt in range(4):
        try:
            req = urllib.request.Request(url, headers={"User-Agent": "FalconAI-history"})
            with urllib.request.urlopen(req, timeout=60) as r:
                return r.read()
        except urllib.error.HTTPError as exc:
            if exc.code == 404:
                return None
            err = f"HTTP {exc.code}"
        except Exception as exc:
            err = str(exc)
        print(f"   retry {attempt + 1}/3 after error: {err}")
        time.sleep(2 * (attempt + 1))
    raise RuntimeError(f"failed to download {url}")


def parse(symbol, interval, raw):
    z = zipfile.ZipFile(io.BytesIO(raw))
    rows = []
    for line in z.read(z.namelist()[0]).decode().splitlines():
        p = line.split(",")
        if not p or not p[0].isdigit():
            continue
        ts = int(p[0])
        if ts > 10**14:  # newer spot files use microseconds
            ts //= 1000
        rows.append((
            symbol, interval, ts,
            float(p[1]), float(p[2]), float(p[3]), float(p[4]),
            float(p[5]), float(p[7]), int(p[8]),
            float(p[9]), float(p[10]), "binance_spot",
        ))
    return rows


def download(db, symbol, interval):
    done = {r[0] for r in db.execute(
        "SELECT month FROM downloaded WHERE symbol=? AND interval=?", (symbol, interval))}
    todo = [m for m in months() if m not in done]
    print(f"{symbol} {interval}: {len(todo)} months to download")
    for month in todo:
        url = f"{BASE}/{symbol}/{interval}/{symbol}-{interval}-{month}.zip"
        raw = fetch(url)
        rows = parse(symbol, interval, raw) if raw else []
        db.executemany(
            "INSERT OR IGNORE INTO candles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)", rows)
        db.execute("INSERT OR REPLACE INTO downloaded VALUES (?,?,?,?)",
                   (symbol, interval, month, len(rows)))
        db.commit()
        print(f"   {month}: {len(rows)} rows")
        time.sleep(0.15)


def fmt(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def summary(db, symbols, intervals):
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for symbol in symbols:
        for interval in intervals:
            step = STEP_MS[interval]
            prev = None
            count = missing = gaps = 0
            first = last = None
            for (ts,) in db.execute(
                "SELECT open_time FROM candles WHERE symbol=? AND interval=? ORDER BY open_time",
                (symbol, interval),
            ):
                if first is None:
                    first = ts
                if prev is not None and ts - prev > step:
                    gaps += 1
                    missing += (ts - prev) // step - 1
                prev = ts
                last = ts
                count += 1
            if count == 0:
                print(f"{symbol} {interval}: NO DATA")
                continue
            print(f"{symbol} {interval}: {count} candles | {fmt(first)} -> {fmt(last)} "
                  f"| gaps: {gaps} (missing candles: {missing})")


def main():
    symbols = sys.argv[1].split(",") if len(sys.argv) > 1 else DEFAULT_SYMBOLS
    intervals = sys.argv[2].split(",") if len(sys.argv) > 2 else DEFAULT_INTERVALS
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    db = sqlite3.connect(DB_PATH)
    db.executescript(SCHEMA)
    for symbol in symbols:
        for interval in intervals:
            download(db, symbol, interval)
    summary(db, symbols, intervals)
    print("DONE")


if __name__ == "__main__":
    main()
