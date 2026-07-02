"""
Falcon AI

RSI Against Reference

Description:
    Validates Falcon RSI implementation.

Version:
    2.0.0
"""

from src.models.candle import Candle
from src.indicators.rsi import RSI

from tests.reference.loader import ReferenceLoader


def build_candles(rows):

    candles = []

    for i, row in enumerate(rows):

        close = float(row["Close"])

        candles.append(

            Candle(

                open_time=i,

                open_price=close,

                high=close,

                low=close,

                close=close,

                volume=0,

                quote_volume=0,

                trades=0,

                taker_buy_base=0,

                taker_buy_quote=0,

            )

        )

    return candles


def main():

    print("=" * 60)
    print("RSI AGAINST REFERENCE")
    print("=" * 60)

    rows = ReferenceLoader.load(
        "tests/reference/datasets/rsi_wilder.csv"
    )

    candles = build_candles(rows)

    indicator = RSI()

    values = indicator.calculate(
        candles,
        period=14
    )

    print()

    print("Dataset :", len(rows))
    print("Candles :", len(candles))
    print("RSI     :", len(values))

    print()

    print("First RSI :", values[14])
    print("Last RSI  :", values[-1])


if __name__ == "__main__":
    main()