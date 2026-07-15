"""
Falcon AI

Decision Engine Tests

Version: 1.0.0
"""

from src.analysis.result import AnalysisResult

from src.analysis.features import FeatureVector

from src.analysis.probability import Probability

from src.analysis.reasoning import ReasonCollection

from src.analysis.decision import DecisionEngine
from src.analysis.decision import DecisionType


def test_buy():

    result = AnalysisResult(

        features=FeatureVector(),

        probability=Probability(

            bullish=0.80,

            bearish=0.10,

            neutral=0.10,

            confidence=0.90,

        ),

        reasons=ReasonCollection(),

    )

    decision = DecisionEngine().evaluate(result)

    assert decision.action == DecisionType.BUY


def test_sell():

    result = AnalysisResult(

        features=FeatureVector(),

        probability=Probability(

            bullish=0.20,

            bearish=0.70,

            neutral=0.10,

            confidence=0.90,

        ),

        reasons=ReasonCollection(),

    )

    decision = DecisionEngine().evaluate(result)

    assert decision.action == DecisionType.SELL


def test_hold():

    result = AnalysisResult(

        features=FeatureVector(),

        probability=Probability(

            bullish=0.50,

            bearish=0.30,

            neutral=0.20,

            confidence=0.85,

        ),

        reasons=ReasonCollection(),

    )

    decision = DecisionEngine().evaluate(result)

    assert decision.action == DecisionType.HOLD


def test_wait():

    result = AnalysisResult(

        features=FeatureVector(),

        probability=Probability(

            bullish=0.90,

            bearish=0.05,

            neutral=0.05,

            confidence=0.40,

        ),

        reasons=ReasonCollection(),

    )

    decision = DecisionEngine().evaluate(result)

    assert decision.action == DecisionType.WAIT


def test_no_trade():

    result = AnalysisResult(

        features=FeatureVector(),

        probability=Probability(

            bullish=0.62,

            bearish=0.20,

            neutral=0.18,

            confidence=0.75,

        ),

        reasons=ReasonCollection(),

    )

    decision = DecisionEngine().evaluate(result)

    assert decision.action == DecisionType.NO_TRADE