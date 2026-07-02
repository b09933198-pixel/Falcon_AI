"""
Falcon AI

Indicators

Simple Moving Average

Version: 3.0.0
"""

from src.models import Candle


class SMA:

    def calculate(
        self,
        candles: list[Candle],
        period: int
    ) -> list[float | None]:

        if period <= 0:
            raise ValueError("period must be greater than zero")

        result = []

        for index in range(len(candles)):

            if index < period - 1:

                result.append(None)
                continue

            total = 0.0

            for i in range(
                index - period + 1,
                index + 1
            ):

                total += candles[i].close

            result.append(total / period)

        return result