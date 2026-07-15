"""
Falcon AI

Analysis Engine

Version: 1.0.0
"""

from src.analysis.probability import ProbabilityEngine
from src.analysis.reasoning import ReasonEngine

from src.analysis.result import AnalysisResultBuilder

from src.analysis.decision import DecisionEngine


class AnalysisEngine:

    def __init__(self):

        self.probability_engine = ProbabilityEngine()

        self.reason_engine = ReasonEngine()

        self.decision_engine = DecisionEngine()

    def run(

        self,

        features,

        symbol="",

        timeframe="",

        exchange="",

        timestamp=0,

    ):

        probability = self.probability_engine.calculate(features)

        reasons = self.reason_engine.build(features)

        analysis = AnalysisResultBuilder.build(

            features=features,

            probability=probability,

            reasons=reasons,

            symbol=symbol,

            timeframe=timeframe,

            exchange=exchange,

            timestamp=timestamp,

        )

        decision = self.decision_engine.evaluate(analysis)

        analysis.decision = decision

        return analysis