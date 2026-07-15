"""
Falcon AI

Swing Detector

Version: 1.0.0
"""

from __future__ import annotations

from .swing import Swing
from .swing_builder import SwingBuilder


class SwingDetectorEngine:

    def detect(
        self,
        candles,
        strength: int = 2,
    ) -> list[Swing]:

        swings: list[Swing] = []

        if len(candles) < strength * 2 + 1:
            return swings

        for i in range(strength, len(candles) - strength):

            high = candles[i].high
            low = candles[i].low

            is_high = True
            is_low = True

            for j in range(1, strength + 1):

                if high <= candles[i - j].high:
                    is_high = False

                if high <= candles[i + j].high:
                    is_high = False

                if low >= candles[i - j].low:
                    is_low = False

                if low >= candles[i + j].low:
                    is_low = False

            if is_high:

                swings.append(

                    SwingBuilder.high(

                        index=i,

                        price=high,

                        timeframe=getattr(candles[i], "timeframe", "Unknown"),

                        timestamp=getattr(candles[i], "timestamp", 0),

                        strength=strength,

                    )

                )

            elif is_low:

                swings.append(

                    SwingBuilder.low(

                        index=i,

                        price=low,

                        timeframe=getattr(candles[i], "timeframe", "Unknown"),

                        timestamp=getattr(candles[i], "timestamp", 0),

                        strength=strength,

                    )

                )

        return swings