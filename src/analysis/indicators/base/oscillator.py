"""
Falcon AI

Oscillator Base

Version: 2.0.0
"""

from .indicator import Indicator


class Oscillator(Indicator):

    category = "Oscillator"

    lower_bound: float = 0.0
    upper_bound: float = 100.0

    def state(self, value: float) -> str:

        if value >= 70:
            return "Overbought"

        if value <= 30:
            return "Oversold"

        return "Neutral"