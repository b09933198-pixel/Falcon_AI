from src.analysis.mtf import (
    Timeframe,
    TimeframeSnapshot,
    TimeframeCollection,
)

from src.analysis.result import AnalysisResultBuilder
from src.analysis.features import FeatureVector
from src.analysis.probability import Probability
from src.analysis.reasoning import ReasonCollection


def build_analysis():

    return AnalysisResultBuilder.build(

        features=FeatureVector(),

        probability=Probability(

            bullish=0.5,

            bearish=0.3,

            neutral=0.2,

            confidence=0.9,

        ),

        reasons=ReasonCollection(),

    )


def test_collection():

    collection = TimeframeCollection()

    h1 = TimeframeSnapshot(

        timeframe=Timeframe.H1,

        analysis=build_analysis(),

    )

    d1 = TimeframeSnapshot(

        timeframe=Timeframe.D1,

        analysis=build_analysis(),

    )

    collection.add(h1)

    collection.add(d1)

    assert len(collection) == 2

    assert collection.get(Timeframe.H1) == h1

    assert collection.get(Timeframe.D1) == d1