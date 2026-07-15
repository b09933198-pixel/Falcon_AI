from src.analysis.mtf import (
    Timeframe,
    TimeframeBuilder,
)

from src.analysis.result import AnalysisResultBuilder
from src.analysis.features import FeatureVector
from src.analysis.probability import Probability
from src.analysis.reasoning import ReasonCollection


def test_builder():

    analysis = AnalysisResultBuilder.build(

        features=FeatureVector(),

        probability=Probability(

            bullish=0.5,

            bearish=0.3,

            neutral=0.2,

            confidence=0.9,

        ),

        reasons=ReasonCollection(),

    )

    snapshot = TimeframeBuilder.build(

        timeframe=Timeframe.H4,

        analysis=analysis,

    )

    assert snapshot.timeframe == Timeframe.H4

    assert snapshot.analysis == analysis