"""
Falcon AI

Risk Builder

Version: 1.0.0
"""

from .risk import RiskResult


class RiskBuilder:

    @staticmethod
    def build(

        risk_percent: float,

        position_size: float,

        stop_loss: float,

        take_profit: float,

        risk_reward: float,

        max_loss: float,

        confidence: float,

        profile: str,

        timeframe: str = "Unknown",

        timestamp: int = 0,

    ):

        return RiskResult(

            risk_percent=risk_percent,

            position_size=position_size,

            stop_loss=stop_loss,

            take_profit=take_profit,

            risk_reward=risk_reward,

            max_loss=max_loss,

            confidence=confidence,

            profile=profile,

            timeframe=timeframe,

            timestamp=timestamp,

        )