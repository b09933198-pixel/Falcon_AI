"""
Falcon AI

Position Size Rule

Version: 1.0.0
"""

from .base import RiskRule


class PositionSizeRule(RiskRule):

    name = "PositionSize"

    weight = 1.0

    def evaluate(

        self,

        context,

        stop_distance: float,

        risk_percent: float = 1.0,

    ):

        balance = context.account.balance

        max_loss = balance * (risk_percent / 100)

        if stop_distance <= 0:

            return 0.0

        return max_loss / stop_distance