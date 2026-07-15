"""
Falcon AI

Enterprise SMA

Version: 2.0.0
"""

from __future__ import annotations

from typing import Sequence

from src.domain.models import Candle
from src.analysis.indicators.base.trend import TrendIndicator


class SMA(TrendIndicator):

    name = "SMA"

    description = "Simple Moving Average"

    version = "2.0.0"

    def calculate(
        self,
        candles: Sequence[Candle],
        period: int,
    ) -> list[float | None]:

        self.validate(candles, period)

        closes = [c.close for c in candles]

        result: list[float | None] = [None] * len(closes)

        for i in range(period - 1, len(closes)):

            result[i] = sum(
                closes[i - period + 1:i + 1]
            ) / period

        return result