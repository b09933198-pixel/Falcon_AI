"""
Falcon AI

Reason Builder

Version: 1.0.0
"""

from .reason import Reason
from .reason_type import ReasonType


class ReasonBuilder:

    @staticmethod
    def build(

        reason_id: str,

        title: str,

        description: str,

        category: ReasonType,

        score: float,

        confidence: float,

        priority: int,

        source: str,

        timeframe: str = "Unknown",

    ) -> Reason:

        return Reason(

            id=reason_id,

            title=title,

            description=description,

            category=category,

            score=score,

            confidence=confidence,

            priority=priority,

            source=source,

            timeframe=timeframe,

        )