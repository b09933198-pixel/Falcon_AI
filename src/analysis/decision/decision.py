from dataclasses import dataclass

from .decision_type import DecisionType


@dataclass(slots=True)
class Decision:

    action: DecisionType

    confidence: float

    score: float

    reason: str

    timeframe: str = "Unknown"

    timestamp: int = 0

    def as_dict(self):

        return {

            "action": self.action.value,

            "confidence": self.confidence,

            "score": self.score,

            "reason": self.reason,

            "timeframe": self.timeframe,

            "timestamp": self.timestamp,

        }