"""
Falcon AI

Exponential Moving Average (EMA)

Version: 1.0.0
"""

from src.indicators.base import Indicator
from src.indicators.sma import SMA


class EMA(Indicator):

    name = "EMA"

    def calculate(
        self,
        candles,
        period: int
    ):

        self.validate(candles, period)

        closes = [c.close for c in candles]

        result = [None] * len(closes)

        sma = SMA()

        first_sma = sma.calculate(
            candles,
            period
        )[period - 1]

        result[period - 1] = first_sma

        multiplier = 2 / (period + 1)

        previous = first_sma

        for i in range(period, len(closes)):

            current = (
                (closes[i] - previous)
                * multiplier
            ) + previous

            result[i] = current

            previous = current

        return result