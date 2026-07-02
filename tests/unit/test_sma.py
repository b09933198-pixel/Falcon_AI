"""
Falcon AI

SMA Unit Test

Version: 2.0.0
"""

from src.models import Candle
from src.indicators import SMA


def candle(price: float):

    return Candle(

        time=0,

        open=price,

        high=price,

        low=price,

        close=price,

        volume=0,

    )


def main():

    print("=" * 60)
    print("SMA UNIT TEST")
    print("=" * 60)

    candles = [

        candle(10),
        candle(20),
        candle(30),
        candle(40),
        candle(50)

    ]

    sma = SMA()

    result = sma.calculate(

        candles,

        period=3

    )

    expected = [

        None,

        None,

        20.0,

        30.0,

        40.0

    ]

    print("Expected :", expected)
    print("Result   :", result)

    print()

    if result == expected:

        print("SUCCESS ✅")

    else:

        print("FAILED ❌")

        print()

        print("Expected :", expected)

        print("Result   :", result)


if __name__ == "__main__":
    main()