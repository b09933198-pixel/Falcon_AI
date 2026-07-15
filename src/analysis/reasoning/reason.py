"""
Falcon AI

Reason Domain

Version: 1.0.0
"""

from dataclasses import dataclass


@dataclass(slots=True)

class Reason:

    id: str

    title: str

    description: str

    category: str

    score: float

    confidence: float

    priority: int

    source: str

    timeframe: str = "Unknown"

    timestamp: int = 0

    def as_dict(self):

        return {

            "id": self.id,

            "title": self.title,

            "description": self.description,

            "category": (
    self.category.value
    if hasattr(self.category, "value")
    else self.category
),

            "score": self.score,

            "confidence": self.confidence,

            "priority": self.priority,

            "source": self.source,

            "timeframe": self.timeframe,

            "timestamp": self.timestamp,

        }