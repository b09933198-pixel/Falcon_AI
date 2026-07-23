"""
Falcon AI

Enterprise RSI Test

Version: 3.0.0
"""

from src.domain.models import Candle
from src.analysis.indicators.oscillator.rsi import RSI


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


def test_rsi_calculation():
    closes = [
        44.34,
        44.09,
        44.15,
        43.61,
        44.33,
        44.83,
        45.10,
        45.42,
        45.84,
        46.08,
        45.89,
        46.03,
        45.61,
        46.28,
        46.28,
    ]

    candles = [candle(x) for x in closes]

    indicator = RSI()

    result = indicator.calculate(
        candles,
        period=14,
    )

    assert len(result) == len(candles)
    assert result[14] is not None