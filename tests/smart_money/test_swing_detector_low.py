from src.analysis.smart_money import SwingDetectorEngine
from src.domain.models import Candle


def candle(high: float, low: float):
    return Candle(
    timestamp=0,
    open=low,
    high=high,
    low=low,
    close=low,
    volume=0,
    quote_volume=0,
    trades=0,
    buy_volume=0,
    buy_quote_volume=0,
)


def test_low():

    candles = [
        candle(30, 20),
        candle(28, 18),
        candle(25, 15),
        candle(22, 10),
        candle(20, 5),
        candle(22, 10),
        candle(25, 15),
        candle(28, 18),
        candle(30, 20),
    ]

    swings = SwingDetectorEngine().detect(candles)

    assert len(swings) == 1
    assert swings[0].is_high is False
    assert swings[0].price == 5