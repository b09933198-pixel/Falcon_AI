"""
Falcon AI

Enterprise RSI

Version: 2.0.0
"""

from __future__ import annotations

from typing import Sequence

from src.domain.models import Candle
from src.analysis.indicators.base import Oscillator


class RSI(Oscillator):

    name = "RSI"

    description = "Relative Strength Index (Wilder)"

    version = "2.0.0"

    def calculate(
        self,
        candles: Sequence[Candle],
        period: int,
    ) -> list[float | None]:

        self.validate(candles, period)

        if len(candles) < period + 1:
            raise ValueError(
                "Not enough candles for RSI."
            )

        closes = [c.close for c in candles]

        gains = []
        losses = []

        for i in range(1, len(closes)):

            delta = closes[i] - closes[i - 1]

            if delta > 0:

                gains.append(delta)
                losses.append(0.0)

            else:

                gains.append(0.0)
                losses.append(abs(delta))

        result: list[float | None] = [None] * len(closes)

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        if avg_loss == 0:

            result[period] = 100.0

        elif avg_gain == 0:

            result[period] = 0.0

        else:

            rs = avg_gain / avg_loss

            result[period] = (
                100 - (100 / (1 + rs))
            )

        for i in range(period + 1, len(closes)):

            gain = gains[i - 1]
            loss = losses[i - 1]

            avg_gain = (
                (avg_gain * (period - 1))
                + gain
            ) / period

            avg_loss = (
                (avg_loss * (period - 1))
                + loss
            ) / period

            if avg_loss == 0:

                result[i] = 100.0

            elif avg_gain == 0:

                result[i] = 0.0

            else:

                rs = avg_gain / avg_loss

                result[i] = (
                    100 - (100 / (1 + rs))
                )

        return result