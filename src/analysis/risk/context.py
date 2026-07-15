"""
Falcon AI

Risk Context

Version: 1.0.0
"""

from dataclasses import dataclass

from .account import Account
from .profile import RiskProfile

from src.analysis.result import AnalysisResult


@dataclass(slots=True)
class RiskContext:

    account: Account

    analysis: AnalysisResult

    profile: RiskProfile

    atr: float = 0.0

    spread: float = 0.0

    volatility: float = 0.0

    def as_dict(self):

        return {

            "account": self.account.as_dict(),

            "analysis": self.analysis.as_dict(),

            "profile": self.profile.value,

            "atr": self.atr,

            "spread": self.spread,

            "volatility": self.volatility,

        }