from src.analysis import AnalysisEngine

from src.analysis.features import Feature
from src.analysis.features import FeatureVector


def test_analysis_engine():

    fv = FeatureVector()

    fv.add(

        Feature(

            id="rsi",

            name="RSI",

            category="Oscillator",

            value=20,

        )

    )

    engine = AnalysisEngine()

    result = engine.run(fv)

    assert result.probability is not None

    assert result.reasons is not None

    assert result.decision is not None