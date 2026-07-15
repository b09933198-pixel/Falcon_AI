"""
Falcon AI

Rule Result

Version: 1.0.0
"""

from dataclasses import dataclass

from src.analysis.reasoning import ReasonType


@dataclass(slots=True)
class RuleResult:

    rule: str

    bullish: float

    bearish: float

    neutral: float

    confidence: float

    reason_id: str

    title: str

    description: str

    category: ReasonType

    priority: int

    timeframe: str = "Unknown"

    timestamp: int = 0

    def as_dict(self):

        return {

            "rule": self.rule,

            "bullish": self.bullish,

            "bearish": self.bearish,

            "neutral": self.neutral,

            "confidence": self.confidence,

            "reason_id": self.reason_id,

            "title": self.title,

            "description": self.description,

            "category": (
                self.category.value
                if hasattr(self.category, "value")
                else self.category
            ),

            "priority": self.priority,

            "timeframe": self.timeframe,

            "timestamp": self.timestamp,

        }