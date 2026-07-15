from src.analysis.result import AnalysisResultBuilder

from src.analysis.features import FeatureVector

from src.analysis.probability import Probability

from src.analysis.reasoning import ReasonCollection

def test_analysis_result_dict():

    result = AnalysisResultBuilder.build(

        features=FeatureVector(),

        probability=Probability(

            bullish=0.5,

            bearish=0.3,

            neutral=0.2,

            confidence=0.9,

        ),

        reasons=ReasonCollection(),

    )

    data = result.as_dict()

    assert "features" in data
    assert "probability" in data
    assert "reasons" in data
    assert "metadata" in data