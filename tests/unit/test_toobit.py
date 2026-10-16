"""
Tests for the Toobit klines client (no network: a fake exchange serves the rows).
"""

import json
import urllib.parse

from src.data.toobit import (
    ToobitError,
    completed_only,
    fetch_klines,
    fetch_recent,
    klines_url,
    parse_kline_row,
    parse_klines,
)

HOUR = 3_600_000
T0 = 1_790_000_000_000 - (1_790_000_000_000 % HOUR)

LIVE_ROW = [1792180800000, "81589.85", "81784.01", "81524.01", "81727.83", "181.88383", 0,
            "14853088.9500025", 1207, "79.07736", "6457043.3098158"]


def row(ts, price=100.0):
    return [ts, str(price), str(price + 1), str(price - 1), str(price + 0.5), "10", 0, "1000", 5, "4", "400"]


def raises(call, error=ToobitError):
    try:
        call()
    except error:
        return True
    return False


class FakeExchange:
    """Serves hourly rows; the last one is still forming. Records every request."""

    def __init__(self, count, forming_last=True):
        self.rows = [row(T0 + k * HOUR, 100 + k) for k in range(count)]
        self.requests = []

    def __call__(self, url, timeout):
        query = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        limit = int(query["limit"][0])
        end = int(query["endTime"][0]) if "endTime" in query else None
        self.requests.append((limit, end))
        rows = [r for r in self.rows if end is None or r[0] <= end]
        return json.dumps(rows[-limit:])


def test_parse_live_row():
    c = parse_kline_row(LIVE_ROW)
    assert c.timestamp == 1792180800000
    assert (c.open, c.high, c.low, c.close) == (81589.85, 81784.01, 81524.01, 81727.83)
    assert c.volume == 181.88383 and c.quote_volume == 14853088.9500025
    assert c.trades == 1207 and c.buy_volume == 79.07736 and c.buy_quote_volume == 6457043.3098158


def test_malformed_rows_are_rejected_not_repaired():
    assert raises(lambda: parse_kline_row([1, 2, 3]))
    assert raises(lambda: parse_kline_row("nope"))
    bad_time = list(LIVE_ROW)
    bad_time[0] = "1792180800000"
    assert raises(lambda: parse_kline_row(bad_time))
    bad_number = list(LIVE_ROW)
    bad_number[2] = "abc"
    assert raises(lambda: parse_kline_row(bad_number))
    high_below_low = list(LIVE_ROW)
    high_below_low[2], high_below_low[3] = "81000", "82000"
    assert raises(lambda: parse_kline_row(high_below_low))
    assert raises(lambda: parse_klines({"code": -1}))
    assert raises(lambda: parse_klines([row(T0 + HOUR), row(T0)]))
    assert raises(lambda: parse_klines([row(T0), row(T0)]))


def test_completed_only_boundary():
    candles = parse_klines([row(T0), row(T0 + HOUR), row(T0 + 2 * HOUR)])
    assert [c.timestamp for c in completed_only(candles, T0 + 2 * HOUR, HOUR)] == [T0, T0 + HOUR]
    assert [c.timestamp for c in completed_only(candles, T0 + 2 * HOUR - 1, HOUR)] == [T0]
    assert completed_only(candles, T0, HOUR) == []


def test_url_and_fetch_klines():
    url = klines_url("BTCUSDT", "1h", 3, 123)
    assert "symbol=BTCUSDT" in url and "interval=1h" in url and "limit=3" in url and "endTime=123" in url
    assert "endTime" not in klines_url("BTCUSDT", "1h", 3)

    exchange = FakeExchange(10)
    candles = fetch_klines("BTCUSDT", "1h", 4, opener=exchange)
    assert len(candles) == 4 and candles[-1].timestamp == T0 + 9 * HOUR

    assert raises(lambda: fetch_klines("BTCUSDT", "1h", opener=lambda u, t: "<html>"))
    assert raises(lambda: fetch_klines("BTCUSDT", "1h", opener=lambda u, t: '{"code": 1}'))


def test_fetch_recent_pages_backwards_and_drops_the_forming_candle():
    exchange = FakeExchange(1300)
    now = T0 + 1299 * HOUR + 40 * 60_000            # the last candle opened 40 minutes ago
    candles = fetch_recent("BTCUSDT", "1h", HOUR, 1000, now, opener=exchange, pause=0, page=500)

    assert len(candles) == 1000
    assert candles[-1].timestamp == T0 + 1298 * HOUR       # newest COMPLETED candle
    assert all(b.timestamp - a.timestamp == HOUR for a, b in zip(candles, candles[1:]))
    assert len(exchange.requests) >= 3 and exchange.requests[0][1] is None
    assert all(end is not None for _, end in exchange.requests[1:])


def test_fetch_recent_stops_when_the_exchange_runs_out_of_history():
    exchange = FakeExchange(120)
    now = T0 + 119 * HOUR + 1
    candles = fetch_recent("BTCUSDT", "1h", HOUR, 1000, now, opener=exchange, pause=0, page=50)
    assert len(candles) == 119 and len(exchange.requests) <= 6
    assert raises(lambda: fetch_recent("BTCUSDT", "1h", HOUR, 0, now, opener=exchange), ValueError)
