"""
Falcon AI

Risk Result

Version: 1.0.0
"""

from dataclasses import dataclass


@dataclass(slots=True)
class RiskResult:

    risk_percent: float

    position_size: float

    stop_loss: float

    take_profit: float

    risk_reward: float

    max_loss: float

    confidence: float

    profile: str

    timeframe: str = "Unknown"

    timestamp: int = 0

    def as_dict(self):

        return {

            "risk_percent": self.risk_percent,

            "position_size": self.position_size,

            "stop_loss": self.stop_loss,

            "take_profit": self.take_profit,

            "risk_reward": self.risk_reward,

            "max_loss": self.max_loss,

            "confidence": self.confidence,

            "profile": self.profile,

            "timeframe": self.timeframe,

            "timestamp": self.timestamp,

        }