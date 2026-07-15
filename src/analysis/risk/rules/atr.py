"""
Falcon AI

ATR Risk Rule

Version: 1.0.0
"""

from .base import RiskRule


class ATRRule(RiskRule):

    name = "ATR"

    weight = 1.0

    DEFAULT_STOP = 100.0

    def evaluate(self, context):

        if context.atr > 0:

            return context.atr * 2

        return self.DEFAULT_STOP