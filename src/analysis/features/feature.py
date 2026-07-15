"""
Falcon AI

Enterprise Feature

Version: 2.0.0
"""

from dataclasses import dataclass


@dataclass(slots=True)
class Feature:
    id: str

    name: str

    category: str

    value: float

    normalized: float | None = None

    weight: float = 1.0

    confidence: float = 1.0

    source: str = "Indicator"

    timeframe: str = "Unknown"

    timestamp: int = 0

    def as_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "value": self.value,
            "normalized": self.normalized,
            "weight": self.weight,
            "confidence": self.confidence,
            "source": self.source,
            "timeframe": self.timeframe,
            "timestamp": self.timestamp,
        }