"""
Falcon AI

Decision Engine

Version: 2.0.0
"""

from .builder import DecisionBuilder
from .decision_type import DecisionType


class DecisionEngine:

    def evaluate(self, analysis):

        probability = analysis.probability

        bullish = probability.bullish
        confidence = probability.confidence

        if confidence < 0.60:

            return DecisionBuilder.build(

                action=DecisionType.WAIT,

                confidence=confidence,

                score=bullish,

                reason="Low confidence",

            )

        if bullish >= 0.70 and confidence >= 0.80:

            return DecisionBuilder.build(

                action=DecisionType.BUY,

                confidence=confidence,

                score=bullish,

                reason="Strong bullish probability",

            )

        if bullish <= 0.30 and confidence >= 0.80:

            return DecisionBuilder.build(

                action=DecisionType.SELL,

                confidence=confidence,

                score=bullish,

                reason="Strong bearish probability",

            )

        if 0.45 <= bullish <= 0.55:

            return DecisionBuilder.build(

                action=DecisionType.HOLD,

                confidence=confidence,

                score=bullish,

                reason="Market neutral",

            )

        return DecisionBuilder.build(

            action=DecisionType.NO_TRADE,

            confidence=confidence,

            score=bullish,

            reason="No clear opportunity",

        )