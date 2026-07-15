"""
Falcon AI

Multi Timeframe Result

Version: 1.0.0
"""

from dataclasses import dataclass


@dataclass(slots=True)
class MultiTimeframeResult:

    probability: object

    agreement: float

    confidence: float

    dominant_action: str

    aligned: bool

    def as_dict(self):

        return {

            "probability": self.probability.as_dict(),

            "agreement": self.agreement,

            "confidence": self.confidence,

            "dominant_action": self.dominant_action,

            "aligned": self.aligned,

        }