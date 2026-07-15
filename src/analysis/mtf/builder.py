"""
Falcon AI

Multi Timeframe Builder

Version: 1.0.0
"""

from __future__ import annotations

from src.analysis.result import AnalysisResult

from .snapshot import TimeframeSnapshot
from .timeframe import Timeframe


class TimeframeBuilder:

    @staticmethod
    def build(
        timeframe: Timeframe,
        analysis: AnalysisResult,
    ) -> TimeframeSnapshot:

        return TimeframeSnapshot(

            timeframe=timeframe,

            analysis=analysis,

        )