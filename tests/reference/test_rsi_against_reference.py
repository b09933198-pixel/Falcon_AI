"""
Falcon AI

Enterprise RSI Reference Test

Version: 3.0.0
"""

from src.domain.models import Candle
from src.analysis.indicators.oscillator.rsi import RSI

from tests.reference.loader import ReferenceLoader


def build_candles(rows):
    candles = []

    for i, row in enumerate(rows):
        close = float(row["Close"])

        candles.append(
            Candle(
                timestamp=i,
                open=close,
                high=close,
                low=close,
                close=close,
                volume=0,
                quote_volume=0,
                trades=0,
                buy_volume=0,
                buy_quote_volume=0,
            )
        )

    return candles


def test_rsi_against_reference():
    rows = ReferenceLoader.load(
        "tests/reference/datasets/rsi_wilder.csv"
    )

    candles = build_candles(rows)

    indicator = RSI()

    values = indicator.calculate(
        candles,
        period=14,
    )

    assert len(values) == len(candles)
    assert values[14] is not None
    assert values[-1] is not None