"""
Falcon AI

Multi Timeframe Engine

Version: 1.0.0
"""

from __future__ import annotations

from src.analysis.result import AnalysisResult

from .builder import TimeframeBuilder
from .collection import TimeframeCollection
from .fusion import FusionEngine
from .timeframe import Timeframe


class MultiTimeframeEngine:

    def __init__(self):

        self.fusion = FusionEngine()

    def run(
        self,
        analyses: dict[Timeframe, AnalysisResult],
    ):

        collection = TimeframeCollection()

        for timeframe, analysis in analyses.items():

            collection.add(

                TimeframeBuilder.build(

                    timeframe,

                    analysis,

                )

            )

        return self.fusion.merge(collection)