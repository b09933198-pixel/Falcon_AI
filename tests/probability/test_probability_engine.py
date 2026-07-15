from src.analysis.features import Feature
from src.analysis.features import FeatureVector

from src.analysis.probability import ProbabilityEngine


def test_probability_engine_returns_probability():

    fv = FeatureVector()

    fv.add(
        Feature(
            id="rsi",
            name="RSI",
            category="Oscillator",
            value=20,
        )
    )

    fv.add(
        Feature(
            id="ema50",
            name="EMA50",
            category="Trend",
            value=62500,
        )
    )

    fv.add(
        Feature(
            id="ema200",
            name="EMA200",
            category="Trend",
            value=62000,
        )
    )

    result = ProbabilityEngine().calculate(fv)

    assert result.bullish > result.bearish

    assert result.confidence > 0

    assert result.model == "WeightedRuleFusion"