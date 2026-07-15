"""
Falcon AI

Reason Engine

Version: 2.0.0
"""

from __future__ import annotations

from .collection import ReasonCollection
from .builder import ReasonBuilder
from .reason_type import ReasonType


class ReasonEngine:

    def build(self, features):

        collection = ReasonCollection()

        rsi = features.get("RSI")

        if rsi:

            if rsi.value < 30:

                collection.add(

                    ReasonBuilder.build(

                        reason_id="rsi_oversold",

                        title="RSI Oversold",

                        description="RSI below 30",

                        category=ReasonType.MOMENTUM,

                        score=0.90,

                        confidence=0.95,

                        priority=1,

                        source="RSIRule",

                    )

                )

            elif rsi.value > 70:

                collection.add(

                    ReasonBuilder.build(

                        reason_id="rsi_overbought",

                        title="RSI Overbought",

                        description="RSI above 70",

                        category=ReasonType.MOMENTUM,

                        score=0.90,

                        confidence=0.95,

                        priority=1,

                        source="RSIRule",

                    )

                )

        return collection

    def sort(
        self,
        collection: ReasonCollection,
    ):

        return collection.sorted()

    def top(
        self,
        collection: ReasonCollection,
        limit: int = 5,
    ):

        return collection.top(limit)

    def summary(
        self,
        collection: ReasonCollection,
    ) -> list[str]:

        return [

            reason.title

            for reason in collection.sorted()

        ]

    def export(
        self,
        collection: ReasonCollection,
    ):

        return collection.as_dict()