from src.analysis.mtf import (
    Timeframe,
    TimeframeSnapshot,
)

from src.analysis.result import AnalysisResultBuilder
from src.analysis.features import FeatureVector
from src.analysis.probability import Probability
from src.analysis.reasoning import ReasonCollection


def test_snapshot():

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

    snap = TimeframeSnapshot(

        timeframe=Timeframe.H1,

        analysis=analysis,

    )

    assert snap.timeframe == Timeframe.H1

    assert snap.analysis == analysis