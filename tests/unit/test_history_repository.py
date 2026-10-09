"""
Tests for CandleRepository.

These are plumbing tests (ordering, ranges, limits, gap handling) on a tiny
fixed fixture. They are NOT numerical validation of any indicator.
"""

import os
import sqlite3
import tempfile

from src.data.history import CandleRepository, HistoryError

HOUR = 3_600_000
BASE = 1_700_000_000_000 - (1_700_000_000_000 % HOUR)

SCHEMA = """
CREATE TABLE candles (
    symbol TEXT NOT NULL, interval TEXT NOT NULL, open_time INTEGER NOT NULL,
    open REAL, high REAL, low REAL, close REAL,
    volume REAL, quote_volume REAL, trades INTEGER,
    buy_volume REAL, buy_quote_volume REAL, source TEXT NOT NULL,
    PRIMARY KEY (symbol, interval, open_time)
);
"""


def _row(symbol, interval, ts, price=100.0):
    return (symbol, interval, ts, price, price + 2, price - 2, price + 1,
            10.0, 1000.0, 5, 4.0, 400.0, "test")


def _make_db(directory, hours, symbol="BTCUSDT", interval="1h"):
    path = os.path.join(directory, "history.db")
    db = sqlite3.connect(path)
    db.executescript(SCHEMA)
    db.executemany(
        "INSERT INTO candles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
        [_row(symbol, interval, BASE + h * HOUR, 100.0 + h) for h in hours],
    )
    db.commit()
    db.close()
    return path


def test_coverage():
    with tempfile.TemporaryDirectory() as d:
        repo = CandleRepository(_make_db(d, range(5)))
        cov = repo.coverage("BTCUSDT", "1h")
        assert cov.count == 5
        assert cov.first == BASE
        assert cov.last == BASE + 4 * HOUR
        empty = repo.coverage("ETHUSDT", "1h")
        assert empty.count == 0 and empty.first is None and empty.last is None
        repo.close()


def test_get_candles_maps_fields_in_order():
    with tempfile.TemporaryDirectory() as d:
        repo = CandleRepository(_make_db(d, range(3)))
        candles = repo.get_candles("BTCUSDT", "1h")
        assert [c.timestamp for c in candles] == [BASE, BASE + HOUR, BASE + 2 * HOUR]
        c = candles[1]
        assert (c.open, c.high, c.low, c.close) == (101.0, 103.0, 99.0, 102.0)
        assert (c.volume, c.quote_volume, c.trades) == (10.0, 1000.0, 5)
        assert (c.buy_volume, c.buy_quote_volume) == (4.0, 400.0)
        repo.close()


def test_start_inclusive_end_exclusive():
    with tempfile.TemporaryDirectory() as d:
        repo = CandleRepository(_make_db(d, range(6)))
        got = repo.get_candles("BTCUSDT", "1h", start=BASE + HOUR, end=BASE + 4 * HOUR)
        assert [c.timestamp for c in got] == [BASE + HOUR, BASE + 2 * HOUR, BASE + 3 * HOUR]
        repo.close()


def test_limit_returns_most_recent_in_ascending_order():
    with tempfile.TemporaryDirectory() as d:
        repo = CandleRepository(_make_db(d, range(10)))
        got = repo.get_candles("BTCUSDT", "1h", limit=3)
        assert [c.timestamp for c in got] == [BASE + 7 * HOUR, BASE + 8 * HOUR, BASE + 9 * HOUR]
        repo.close()


def test_segments_split_at_gaps():
    with tempfile.TemporaryDirectory() as d:
        hours = [0, 1, 2, 5, 6, 10]
        repo = CandleRepository(_make_db(d, hours))
        segs = list(repo.segments("BTCUSDT", "1h"))
        assert [len(s) for s in segs] == [3, 2, 1]
        assert segs[1][0].timestamp == BASE + 5 * HOUR
        repo.close()


def test_segments_without_gaps_is_one_segment():
    with tempfile.TemporaryDirectory() as d:
        repo = CandleRepository(_make_db(d, range(8)))
        segs = list(repo.segments("BTCUSDT", "1h"))
        assert len(segs) == 1 and len(segs[0]) == 8
        repo.close()


def test_misaligned_candles_raise():
    with tempfile.TemporaryDirectory() as d:
        path = _make_db(d, [0, 1])
        db = sqlite3.connect(path)
        db.execute(
            "INSERT INTO candles VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            _row("BTCUSDT", "1h", BASE + HOUR + 1000),
        )
        db.commit()
        db.close()
        repo = CandleRepository(path)
        try:
            list(repo.segments("BTCUSDT", "1h"))
        except HistoryError:
            repo.close()
            return
        raise AssertionError("expected HistoryError")


def test_missing_database_raises():
    with tempfile.TemporaryDirectory() as d:
        try:
            CandleRepository(os.path.join(d, "nope.db"))
        except HistoryError:
            return
        raise AssertionError("expected HistoryError")


def test_invalid_interval_and_limit_raise():
    with tempfile.TemporaryDirectory() as d:
        repo = CandleRepository(_make_db(d, range(3)))
        for call in (
            lambda: repo.get_candles("BTCUSDT", "1x"),
            lambda: repo.get_candles("BTCUSDT", "1h", limit=0),
        ):
            try:
                call()
            except ValueError:
                continue
            raise AssertionError("expected ValueError")
        repo.close()


def test_repository_is_read_only():
    with tempfile.TemporaryDirectory() as d:
        repo = CandleRepository(_make_db(d, range(2)))
        try:
            repo._conn.execute("DELETE FROM candles")
        except sqlite3.OperationalError:
            repo.close()
            return
        raise AssertionError("repository must not allow writes")
