"""
Falcon AI

Risk Engine

Version: 2.0.0
"""

from .builder import RiskBuilder
from .rules import RiskRuleRegistry


class RiskEngine:

    DEFAULT_RISK_PERCENT = 1.0

    DEFAULT_RISK_REWARD = 2.0

    def __init__(self):

        self.registry = RiskRuleRegistry()

    def evaluate(self, context):

        results = {}

        atr_rule = None
        position_rule = None
        tp_rule = None

        for rule in self.registry.all():

            if rule.name == "ATR":
                atr_rule = rule

            elif rule.name == "PositionSize":
                position_rule = rule

            elif rule.name == "TakeProfit":
                tp_rule = rule

        stop_loss = atr_rule.evaluate(context)

        position_size = position_rule.evaluate(

            context,

            stop_distance=stop_loss,

            risk_percent=self.DEFAULT_RISK_PERCENT,

        )

        take_profit = tp_rule.evaluate(

            context,

            stop_distance=stop_loss,

            risk_reward=self.DEFAULT_RISK_REWARD,

        )

        balance = context.account.balance

        max_loss = balance * (

            self.DEFAULT_RISK_PERCENT / 100

        )

        return RiskBuilder.build(

            risk_percent=self.DEFAULT_RISK_PERCENT,

            position_size=position_size,

            stop_loss=stop_loss,

            take_profit=take_profit,

            risk_reward=self.DEFAULT_RISK_REWARD,

            max_loss=max_loss,

            confidence=context.analysis.probability.confidence,

            profile=context.profile.value,

            timeframe=context.analysis.metadata.timeframe,

            timestamp=context.analysis.metadata.timestamp,

        )