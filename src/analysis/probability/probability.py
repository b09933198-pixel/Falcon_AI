"""
Falcon AI

Enterprise Probability

Version: 2.0.0
"""

from dataclasses import dataclass


@dataclass(slots=True)
class Probability:

    bullish: float

    bearish: float

    neutral: float

    confidence: float

    model: str = "IndicatorFusion"

    timeframe: str = "Unknown"

    timestamp: int = 0

    def validate(self):

        total = (
            self.bullish
            + self.bearish
            + self.neutral
        )

        if abs(total - 1.0) > 0.001:
            raise ValueError(
                "Probabilities must sum to 1.0"
            )

        if not (0 <= self.confidence <= 1):
            raise ValueError(
                "Confidence must be between 0 and 1"
            )

    def as_dict(self):

        return {
            "bullish": self.bullish,
            "bearish": self.bearish,
            "neutral": self.neutral,
            "confidence": self.confidence,
            "model": self.model,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp,
        }