from src.analysis.features import Feature
from src.analysis.features import FeatureVector

from src.analysis.probability.rules import TrendRule


def test_trend_positive():

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

    fv.add(
        Feature(
            id="sma50",
            name="SMA50",
            category="Trend",
            value=62400,
        )
    )

    fv.add(
        Feature(
            id="sma200",
            name="SMA200",
            category="Trend",
            value=61900,
        )
    )

    result = TrendRule().evaluate(fv)

    assert result.bullish > result.bearish

    assert result.reason_id == "trend_bullish"

    assert result.category.value == "Trend"

    assert result.confidence > 0.9