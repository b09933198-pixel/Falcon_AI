from dataclasses import dataclass

from src.analysis.result import AnalysisResult

from .timeframe import Timeframe


@dataclass(slots=True)
class TimeframeSnapshot:

    timeframe: Timeframe

    analysis: AnalysisResult

    def as_dict(self):

        return {

            "timeframe": self.timeframe.value,

            "analysis": self.analysis.as_dict(),

        }