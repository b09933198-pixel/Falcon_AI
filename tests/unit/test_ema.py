"""
Falcon AI

Enterprise EMA Test

Version: 3.0.0
"""

from src.domain.models import Candle
from src.analysis.indicators.trend.ema import EMA


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


def test_ema_calculation():
    candles = [
        candle(10),
        candle(20),
        candle(30),
        candle(40),
        candle(50),
    ]

    indicator = EMA()

    result = indicator.calculate(
        candles,
        period=3,
    )

    assert result[0] is None
    assert result[1] is None
    assert result[2] == 20.0
    assert result[3] is not None
    assert result[4] is not None