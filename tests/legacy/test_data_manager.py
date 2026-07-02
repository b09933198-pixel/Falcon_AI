"""
Falcon AI

Data Manager Test

Version: 1.0.0
"""

from src.data import DataManager


def main():

    print("=" * 60)
    print("DATA MANAGER TEST")
    print("=" * 60)

    manager = DataManager()

    candles = manager.get_candles(

        symbol="BTCUSDT",
        interval="1h",
        limit=5

    )

    if candles is None:

        print("FAILED")
        return

    print("SUCCESS")
    print()

    print("Candles :", len(candles))
    print()

    last = candles[-1]

    print("Open  :", last.open)
    print("High  :", last.high)
    print("Low   :", last.low)
    print("Close :", last.close)

    print()

    print(last)


if __name__ == "__main__":
    main()