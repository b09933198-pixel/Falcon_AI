"""
Falcon AI

Take Profit Rule

Version: 1.0.0
"""

from .base import RiskRule


class TakeProfitRule(RiskRule):

    name = "TakeProfit"

    weight = 1.0

    DEFAULT_RR = 2.0

    def evaluate(

        self,

        context,

        stop_distance: float,

        risk_reward: float = DEFAULT_RR,

    ):

        return stop_distance * risk_reward