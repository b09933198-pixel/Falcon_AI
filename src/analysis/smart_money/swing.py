"""
Falcon AI

Swing Point

Version: 1.1.0
"""

from dataclasses import dataclass


@dataclass(slots=True)
class Swing:

    index: int

    price: float

    is_high: bool

    strength: int = 2

    timeframe: str = "Unknown"

    timestamp: int = 0

    @property
    def confirmed_index(self) -> int:
        """Index of the candle at which this swing first becomes knowable.

        A swing needs `strength` candles to its right before it can be
        recognised, so analysis standing at candle N may only use swings
        whose confirmed_index <= N.
        """

        return self.index + self.strength

    def as_dict(self):

        return {

            "index": self.index,

            "price": self.price,

            "is_high": self.is_high,

            "strength": self.strength,

            "timeframe": self.timeframe,

            "timestamp": self.timestamp,

            "confirmed_index": self.confirmed_index,

        }
