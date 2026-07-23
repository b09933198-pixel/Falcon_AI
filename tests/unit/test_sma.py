"""
Falcon AI

Enterprise SMA Test

Version: 3.0.0
"""

from src.domain.models import Candle
from src.analysis.indicators.trend.sma import SMA


def candle(price: float):
    return Candle(
        timestamp=0,
        open=price,
        high=price,
        low=price,
        close=price,
        volume=0.0,
        quote_volume=0.0,
        trades=0,
        buy_volume=0.0,
        buy_quote_volume=0.0,
    )


def test_sma_calculation():
    candles = [
        candle(10),
        candle(20),
        candle(30),
        candle(40),
        candle(50),
    ]

    indicator = SMA()

    result = indicator.calculate(
        candles,
        period=3,
    )

    expected = [
        None,
        None,
        20.0,
        30.0,
        40.0,
    ]

    assert result == expected