"""
Falcon AI

Trading Strategy Result

Version: 1.0.0
"""

from dataclasses import dataclass

from src.analysis.result import AnalysisResult
from src.analysis.decision import Decision
from src.analysis.risk import RiskResult


@dataclass(slots=True)
class TradingPlan:

    analysis: AnalysisResult

    decision: Decision

    risk: RiskResult

    def as_dict(self):

        return {

            "analysis": self.analysis.as_dict(),

            "decision": self.decision.as_dict(),

            "risk": self.risk.as_dict(),

        }