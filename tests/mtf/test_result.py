from src.analysis.mtf.result_builder import MultiTimeframeResultBuilder
from src.analysis.probability import Probability


def test_result():

    result = MultiTimeframeResultBuilder.build(

        probability=Probability(

            bullish=0.7,

            bearish=0.2,

            neutral=0.1,

            confidence=0.9,

        ),

        agreement=0.8,

        confidence=0.9,

        dominant_action="BUY",

        aligned=True,

    )

    assert result.aligned is True

    assert result.dominant_action == "BUY"