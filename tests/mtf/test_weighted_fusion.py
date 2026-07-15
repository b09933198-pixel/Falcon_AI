from src.analysis.mtf import (
    FusionEngine,
    TimeframeBuilder,
    TimeframeCollection,
    Timeframe,
)

from src.analysis.result import AnalysisResultBuilder
from src.analysis.features import FeatureVector
from src.analysis.probability import Probability
from src.analysis.reasoning import ReasonCollection


def build(prob):

    return AnalysisResultBuilder.build(

        features=FeatureVector(),

        probability=prob,

        reasons=ReasonCollection(),

    )


def test_weighted_probability():

    collection = TimeframeCollection()

    collection.add(

        TimeframeBuilder.build(

            Timeframe.H1,

            build(

                Probability(

                    bullish=1,

                    bearish=0,

                    neutral=0,

                    confidence=1,

                )

            ),

        )

    )

    collection.add(

        TimeframeBuilder.build(

            Timeframe.D1,

            build(

                Probability(

                    bullish=0,

                    bearish=1,

                    neutral=0,

                    confidence=1,

                )

            ),

        )

    )

    result = FusionEngine().merge(collection)

    assert result.probability.bearish > result.probability.bullish