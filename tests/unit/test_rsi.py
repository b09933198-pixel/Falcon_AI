"""
Falcon AI

RSI Unit Test

Version: 1.0.0
"""

from src.models import Candle
from src.indicators.rsi import RSI


def candle(price):

    return Candle(

        open_time=0,

        open_price=price,

        high=price,

        low=price,

        close=price,

        volume=0,

        quote_volume=0,

        trades=0,

        taker_buy_base=0,

        taker_buy_quote=0

    )


def main():

    print("=" * 60)
    print("RSI UNIT TEST")
    print("=" * 60)

    closes = [

        44.34,
        44.09,
        44.15,
        43.61,
        44.33,
        44.83,
        45.10,
        45.42,
        45.84,
        46.08,
        45.89,
        46.03,
        45.61,
        46.28,
        46.28

    ]

    candles = [candle(x) for x in closes]

    rsi = RSI()

    result = rsi.calculate(

        candles,

        period=14

    )

    print()

    print(result)

    print()

    print("SUCCESS ✅")


if __name__ == "__main__":
    main()