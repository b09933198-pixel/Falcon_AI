"""
Falcon AI

Trading Plan Builder

Version: 1.0.0
"""

from .strategy import TradingPlan


class TradingPlanBuilder:

    @staticmethod
    def build(

        analysis,

        decision,

        risk,

    ):

        return TradingPlan(

            analysis=analysis,

            decision=decision,

            risk=risk,

        )