"""
Falcon AI

Data Layer

Toobit market-data client (public klines, read-only, standard library only)

Version: 1.0.0

Rules
-----
  - Parsing is strict: a malformed or self-contradictory row raises ToobitError.
    Nothing is repaired, clipped or guessed.
  - The newest candle returned by the exchange is usually still forming. Use
    `completed_only` (done by `fetch_recent`) so an unfinished candle is never stored.
  - No API key and no trading endpoint is used.

Row layout (verified live on 2026-10-16):
  [open_time_ms, open, high, low, close, base_volume, 0, quote_volume, trades,
   taker_buy_base_volume, taker_buy_quote_volume]
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Callable, Dict, List, Optional, Sequence

from src.domain.models import Candle

BASE_URL = "https://api.toobit.com"
KLINES_PATH = "/quote/v1/klines"
PAGE_SIZE = 500


class ToobitError(Exception):
    """The exchange answered something that cannot be trusted or used."""


def klines_url(symbol: str, interval: str, limit: int, end_time: Optional[int] = None) -> str:

    params = {"symbol": symbol, "interval": interval, "limit": limit}

    if end_time is not None:
        params["endTime"] = end_time

    return BASE_URL + KLINES_PATH + "?" + urllib.parse.urlencode(params)


def parse_kline_row(row: Sequence) -> Candle:

    if not isinstance(row, (list, tuple)) or len(row) < 11:
        raise ToobitError(f"unexpected kline row: {str(row)[:80]}")

    stamp = row[0]

    if isinstance(stamp, bool) or not isinstance(stamp, int):
        raise ToobitError(f"bad open time: {stamp!r}")

    try:
        return Candle(
            timestamp=stamp,
            open=float(row[1]),
            high=float(row[2]),
            low=float(row[3]),
            close=float(row[4]),
            volume=float(row[5]),
            quote_volume=float(row[7]),
            trades=int(row[8]),
            buy_volume=float(row[9]),
            buy_quote_volume=float(row[10]),
        )
    except (TypeError, ValueError) as exc:
        raise ToobitError(f"invalid kline row at {stamp}: {exc}") from exc


def parse_klines(payload) -> List[Candle]:
    """Candles of one response, strictly increasing in time."""

    if not isinstance(payload, list):
        raise ToobitError(f"unexpected payload: {str(payload)[:80]}")

    candles = [parse_kline_row(row) for row in payload]

    for previous, current in zip(candles, candles[1:]):
        if current.timestamp <= previous.timestamp:
            raise ToobitError("klines are not strictly increasing in time")

    return candles


def completed_only(candles: Sequence[Candle], now_ms: int, interval_ms: int) -> List[Candle]:
    """Candles whose whole period is over at `now_ms`."""

    return [c for c in candles if c.timestamp + interval_ms <= now_ms]


def _urlopen_body(url: str, timeout: float) -> str:

    request = urllib.request.Request(url, headers={"User-Agent": "FalconAI"})

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        raise ToobitError(f"HTTP {exc.code}") from exc
    except Exception as exc:
        raise ToobitError(f"connection error: {exc}") from exc


def fetch_klines(
    symbol: str,
    interval: str,
    limit: int = PAGE_SIZE,
    end_time: Optional[int] = None,
    opener: Optional[Callable[[str, float], str]] = None,
    timeout: float = 15.0,
) -> List[Candle]:

    body = (opener or _urlopen_body)(klines_url(symbol, interval, limit, end_time), timeout)

    try:
        payload = json.loads(body)
    except ValueError as exc:
        raise ToobitError("response is not JSON") from exc

    return parse_klines(payload)


def fetch_recent(
    symbol: str,
    interval: str,
    interval_ms: int,
    count: int,
    now_ms: int,
    opener: Optional[Callable[[str, float], str]] = None,
    pause: float = 0.35,
    page: int = PAGE_SIZE,
    max_pages: int = 40,
) -> List[Candle]:
    """The latest `count` COMPLETED candles, oldest first (pages backwards in time)."""

    if count < 1:
        raise ValueError("count must be >= 1")

    found: Dict[int, Candle] = {}
    end_time: Optional[int] = None

    for _ in range(max_pages):

        batch = fetch_klines(symbol, interval, page, end_time, opener)

        if not batch:
            break

        for candle in completed_only(batch, now_ms, interval_ms):
            found[candle.timestamp] = candle

        oldest = batch[0].timestamp

        if len(found) >= count or (end_time is not None and oldest >= end_time + 1):
            break

        end_time = oldest - 1

        if pause:
            time.sleep(pause)

    ordered = [found[t] for t in sorted(found)]

    return ordered[-count:]
