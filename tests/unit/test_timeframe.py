"""Tests for interval parsing."""

from src.market.timeframe import interval_to_ms


def test_known_intervals():
    assert interval_to_ms("1m") == 60_000
    assert interval_to_ms("15m") == 900_000
    assert interval_to_ms("1h") == 3_600_000
    assert interval_to_ms("4h") == 14_400_000
    assert interval_to_ms("1d") == 86_400_000
    assert interval_to_ms("1w") == 604_800_000


def test_unusual_but_valid_interval():
    assert interval_to_ms("3h") == 10_800_000


def _must_fail(value):
    try:
        interval_to_ms(value)
    except ValueError:
        return
    raise AssertionError(f"expected ValueError for {value!r}")


def test_invalid_intervals_are_rejected():
    for value in ["", "m", "15", "0m", "-1h", "1x", "1M", "abc", None, 5]:
        _must_fail(value)
