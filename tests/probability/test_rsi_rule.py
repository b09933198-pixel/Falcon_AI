from src.analysis.features import Feature
from src.analysis.features import FeatureVector

from src.analysis.probability.rules import RSIRule


def test_rsi_oversold():

    fv = FeatureVector()

    fv.add(
        Feature(
            id="rsi",
            name="RSI",
            category="Oscillator",
            value=20,
        )
    )

    result = RSIRule().evaluate(fv)

    assert result.bullish > result.bearish

    assert result.reason_id == "rsi_signal"

    assert result.title == "RSI Signal"

    assert result.confidence > 0.8