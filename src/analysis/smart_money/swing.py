"""
Falcon AI

Swing Point

Version: 1.0.0
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

    def as_dict(self):

        return {

            "index": self.index,

            "price": self.price,

            "is_high": self.is_high,

            "strength": self.strength,

            "timeframe": self.timeframe,

            "timestamp": self.timestamp,

        }