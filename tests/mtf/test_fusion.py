from src.analysis.mtf import (
    Timeframe,
    TimeframeBuilder,
    TimeframeCollection,
    FusionEngine,
)

from src.analysis.result import AnalysisResultBuilder
from src.analysis.features import FeatureVector
from src.analysis.probability import Probability
from src.analysis.reasoning import ReasonCollection


def build():

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


def test_fusion():

    collection = TimeframeCollection()

    collection.add(

        TimeframeBuilder.build(

            Timeframe.H1,

            build(),

        )

    )

    collection.add(

        TimeframeBuilder.build(

            Timeframe.H4,

            build(),

        )

    )

    fusion = FusionEngine()

    result = fusion.merge(collection)

    assert result is not None