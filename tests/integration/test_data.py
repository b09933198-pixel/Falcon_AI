"""
Falcon AI

Data Layer Test

Version: 2.1.0
"""

from src.data import DataManager
from src.models import Candle


def main():

    print("=" * 60)
    print("DATA LAYER TEST")
    print("=" * 60)

    manager = DataManager()

    candles = manager.get_candles(
        symbol="BTCUSDT",
        interval="1h",
        limit=5
    )

    if candles is None:
        print("FAILED")
        print("Returned None")
        return

    if len(candles) == 0:
        print("FAILED")
        print("Empty candle list")
        return

    first = candles[0]

    if not isinstance(first, Candle):
        print("FAILED")
        print("Invalid object:", type(first))
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