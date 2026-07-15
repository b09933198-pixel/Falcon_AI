"""
Falcon AI

Enterprise EMA

Version: 2.0.0
"""

from __future__ import annotations

from typing import Sequence

from src.domain.models import Candle

from src.analysis.indicators.base.trend import TrendIndicator
from src.analysis.indicators.trend.sma import SMA


class EMA(TrendIndicator):

    name = "EMA"

    description = "Exponential Moving Average"

    version = "2.0.0"

    def calculate(
        self,
        candles: Sequence[Candle],
        period: int,
    ) -> list[float | None]:

        self.validate(candles, period)

        closes = [c.close for c in candles]

        result: list[float | None] = [None] * len(closes)

        sma = SMA()

        first = sma.calculate(
            candles,
            period,
        )[period - 1]

        result[period - 1] = first

        multiplier = 2 / (period + 1)

        previous = first

        for i in range(period, len(closes)):

            current = (
                (closes[i] - previous)
                * multiplier
            ) + previous

            result[i] = current

            previous = current

        return result