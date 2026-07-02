"""
Falcon AI

Market Layer Test

Version: 2.0.0
"""

from src.market.candles import CandleService
from src.models import Candle


def main():

    print("=" * 60)
    print("MARKET LAYER TEST")
    print("=" * 60)

    service = CandleService()

    candles = service.get_klines(

        symbol="BTCUSDT",
        interval="1h",
        limit=5

    )

    if candles is None:

        print("FAILED")
        return

    if len(candles) == 0:

        print("FAILED")
        print("No candles returned.")
        return

    first = candles[0]

    if not isinstance(first, Candle):

        print("FAILED")
        print("Returned object is not Candle.")
        print(type(first))
        return

    print("SUCCESS")
    print()

    print("Count :", len(candles))
    print("Type  :", type(first))

    print()

    print("Time   :", first.time)
    print("Open   :", first.open)
    print("High   :", first.high)
    print("Low    :", first.low)
    print("Close  :", first.close)
    print("Volume :", first.volume)

    print()

    print(first)


if __name__ == "__main__":
    main()