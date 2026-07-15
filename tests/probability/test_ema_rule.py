from src.analysis.features import Feature
from src.analysis.features import FeatureVector

from src.analysis.probability.rules import EMARule


def test_ema_bullish():

    fv = FeatureVector()

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

    result = EMARule().evaluate(fv)

    assert result.bullish > result.bearish

    assert result.reason_id == "ema_bullish"

    assert result.category.value == "Trend"

    assert result.confidence > 0.7