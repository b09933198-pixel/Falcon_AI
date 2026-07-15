"""
Falcon AI

MTF Fusion Engine

Version: 2.0.0
"""

from __future__ import annotations

from src.analysis.probability import Probability
from src.analysis.reasoning import ReasonCollection

from .collection import TimeframeCollection
from .weights import TIMEFRAME_WEIGHTS


class FusionEngine:

    def merge(
        self,
        collection: TimeframeCollection,
    ):

        snapshots = sorted(

    collection.all(),

    key=lambda snapshot: TIMEFRAME_WEIGHTS[snapshot.timeframe],

)

        total_weight = 0

        bullish = 0.0
        bearish = 0.0
        neutral = 0.0
        confidence = 0.0

        reasons = ReasonCollection()

        last = snapshots[-1].analysis

        for snapshot in snapshots:

            weight = TIMEFRAME_WEIGHTS[snapshot.timeframe]

            total_weight += weight

            probability = snapshot.analysis.probability

            bullish += probability.bullish * weight
            bearish += probability.bearish * weight
            neutral += probability.neutral * weight
            confidence += probability.confidence * weight

            for reason in snapshot.analysis.reasons:

                reasons.add(reason)

        last.probability = Probability(

            bullish=bullish / total_weight,

            bearish=bearish / total_weight,

            neutral=neutral / total_weight,

            confidence=confidence / total_weight,

        )

        last.reasons = reasons

        return last