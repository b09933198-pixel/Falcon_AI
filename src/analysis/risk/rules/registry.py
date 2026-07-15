"""
Falcon AI

Risk Rule Registry

Version: 1.0.0
"""

from .atr import ATRRule
from .position import PositionSizeRule
from .take_profit import TakeProfitRule


class RiskRuleRegistry:

    def __init__(self):

        self._rules = [

            ATRRule(),

            PositionSizeRule(),

            TakeProfitRule(),

        ]

    def all(self):

        return self._rules