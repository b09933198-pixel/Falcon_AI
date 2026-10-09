"""
Falcon AI

Swing Detector

Version: 1.1.0

Rules
-----
A candle i is a swing HIGH when its high is strictly greater than the highs
of the `strength` candles on its left AND greater than or equal to the highs
of the `strength` candles on its right. Swing LOW is the mirror image.

    - Equal highs (a plateau) produce exactly one swing: the first candle.
    - One candle can be both a swing high and a swing low (outside bar);
      both are returned, high first.
    - A swing at index i is only recognisable at index i + strength.
      Never read a swing before Swing.confirmed_index (see confirmed_swings).
    - detect() expects one contiguous run of candles. Never pass candles that
      span a data gap; split them first (CandleRepository.segments).
"""

from __future__ import annotations

from .swing import Swing
from .swing_builder import SwingBuilder


def confirmed_swings(swings: list[Swing], index: int) -> list[Swing]:
    """Swings that were already knowable when standing at candle `index`."""

    return [s for s in swings if s.confirmed_index <= index]


class SwingDetectorEngine:

    def detect(
        self,
        candles,
        strength: int = 2,
        timeframe: str = "Unknown",
    ) -> list[Swing]:

        if not isinstance(strength, int) or strength < 1:
            raise ValueError("strength must be an integer >= 1")

        swings: list[Swing] = []

        count = len(candles)

        if count < strength * 2 + 1:
            return swings

        highs = [c.high for c in candles]
        lows = [c.low for c in candles]

        for i in range(strength, count - strength):

            high = highs[i]
            low = lows[i]

            is_high = (
                high > max(highs[i - strength:i])
                and high >= max(highs[i + 1:i + strength + 1])
            )

            is_low = (
                low < min(lows[i - strength:i])
                and low <= min(lows[i + 1:i + strength + 1])
            )

            if is_high:

                swings.append(
                    SwingBuilder.high(
                        index=i,
                        price=high,
                        strength=strength,
                        timeframe=timeframe,
                        timestamp=candles[i].timestamp,
                    )
                )

            if is_low:

                swings.append(
                    SwingBuilder.low(
                        index=i,
                        price=low,
                        strength=strength,
                        timeframe=timeframe,
                        timestamp=candles[i].timestamp,
                    )
                )

        return swings
