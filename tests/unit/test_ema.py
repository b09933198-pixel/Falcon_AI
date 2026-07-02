"""
Falcon AI

EMA Unit Test

Version: 2.0.0
"""

from src.models import Candle
from src.indicators.ema import EMA


def make_candle(close):

    return Candle(

        time=0,

        open=close,

        high=close,

        low=close,

        close=close,

        volume=1,

    )


def main():

    print("=" * 60)
    print("EMA UNIT TEST")
    print("=" * 60)

    closes = [10, 20, 30, 40, 50, 60]

    candles = [

        make_candle(price)

        for price in closes

    ]

    ema = EMA()

    result = ema.calculate(

        candles,

        period=3

    )

    print("Result :")

    for value in result:

        print(value)

    expected = [

        None,

        None,

        20.0,

        30.0,

        40.0,

        50.0

    ]

    success = True

    for r, e in zip(result, expected):

        if r is None and e is None:

            continue

        if abs(r - e) > 0.0001:

            success = False

            break

    print()

    if success:

        print("SUCCESS ✅")

    else:

        print("FAILED ❌")

        print("Expected:", expected)

        print("Result  :", result)


if __name__ == "__main__":
    main()