import pytest
from types import SimpleNamespace as C

from src.lab.carry_risk import HOUR_MS, max_rise, summarize


def candles(prices):
    return [C(timestamp=i * HOUR_MS, open=o, high=h) for i, (o, h) in enumerate(prices)]


def test_max_rise_uses_entry_open_and_window_highs():
    cs = candles([(100, 105), (101, 120), (110, 150), (120, 400)])
    assert max_rise(cs, 0, 3 * HOUR_MS) == pytest.approx(0.5)      # candle 3 is outside the trade
    assert max_rise(cs, HOUR_MS, 3 * HOUR_MS) == pytest.approx(150 / 101 - 1)


def test_max_rise_none_without_a_candle_at_the_entry():
    cs = candles([(100, 105), (101, 120)])
    assert max_rise(cs, 5 * HOUR_MS, 9 * HOUR_MS) is None
    assert max_rise(cs, 0, 0) is None
    gap = [C(timestamp=10 * HOUR_MS, open=100, high=110)]
    assert max_rise(gap, 0, 20 * HOUR_MS) is None                  # first candle is 10 hours after the entry


def test_summarize_shares_and_quantiles():
    s = summarize([0.0, 0.1, 0.2, 0.35, 0.6, 1.2])
    assert s["n"] == 6 and s["max"] == pytest.approx(1.2)
    assert s["share_ge_30"] == pytest.approx(3 / 6)
    assert s["share_ge_50"] == pytest.approx(2 / 6)
    assert s["share_ge_90"] == pytest.approx(1 / 6)
    assert summarize([]) == {"n": 0}
