"""Falcon AI - Toobit History Probe (read-only, standard library only)."""

from __future__ import annotations

import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone

BASE_URL = "https://api.toobit.com"
KLINES_PATH = "/quote/v1/klines"
MAX_PAGES = 400
PAUSE_SECONDS = 0.35


def fetch(symbol, interval, limit, end_time=None):
    params = {"symbol": symbol, "interval": interval, "limit": limit}
    if end_time is not None:
        params["endTime"] = end_time

    url = BASE_URL + KLINES_PATH + "?" + urllib.parse.urlencode(params)
    request = urllib.request.Request(url, headers={"User-Agent": "FalconAI-probe"})

    try:
        with urllib.request.urlopen(request, timeout=15) as response:
            body = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        return None, f"HTTP {exc.code}: {exc.read()[:120]!r}"
    except Exception as exc:
        return None, f"connection error: {exc}"

    try:
        data = json.loads(body)
    except ValueError:
        return None, "response is not JSON"

    if not isinstance(data, list):
        return None, f"unexpected payload: {str(data)[:120]}"

    return data, None


def fmt(ms):
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def probe(symbol, interval):
    print("=" * 60)
    print(f"PROBE  {symbol}  {interval}")
    print("=" * 60)

    rows, error = fetch(symbol, interval, 1000)

    if error:
        print("FAILED first request:", error)
        return

    if not rows:
        print("Empty response.")
        return

    print(f"Rows returned with limit=1000 : {len(rows)}")
    print(f"Columns per row               : {len(rows[0])}")
    print(f"First row sample              : {rows[0]}")
    order = "ascending" if rows[0][0] < rows[-1][0] else "descending"
    print(f"Order                         : {order}")
    print(f"Range of this page            : {fmt(rows[0][0])} -> {fmt(rows[-1][0])}")

    oldest = min(r[0] for r in rows)
    total = len(rows)
    pages = 1
    stopped_because = "max pages reached"

    while pages < MAX_PAGES:
        time.sleep(PAUSE_SECONDS)

        page, error = fetch(symbol, interval, 1000, end_time=oldest - 1)

        if error:
            stopped_because = f"error: {error}"
            break

        if not page:
            stopped_because = "no more data (reached the start of history)"
            break

        page_oldest = min(r[0] for r in page)

        if page_oldest >= oldest:
            stopped_because = "endTime seems IGNORED (no older data returned)"
            break

        total += len(page)
        oldest = page_oldest
        pages += 1

    print("-" * 60)
    print(f"Pages fetched    : {pages}")
    print(f"Total candles    : {total}")
    print(f"Oldest candle    : {fmt(oldest)} UTC")
    print(f"Stopped because  : {stopped_because}")
    print("-" * 60)


def main():
    symbol = sys.argv[1] if len(sys.argv) > 1 else "BTCUSDT"
    intervals = [sys.argv[2]] if len(sys.argv) > 2 else ["15m", "1h", "4h", "1d"]

    for interval in intervals:
        probe(symbol, interval)
        time.sleep(PAUSE_SECONDS)

    print("DONE. Send this whole output back.")


if __name__ == "__main__":
    main()
