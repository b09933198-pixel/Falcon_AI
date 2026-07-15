"""
Falcon AI

Data Manager Unit Test

Version: 1.0.0
"""

from src.data import DataManager


def main():

    print("=" * 60)
    print("DATA MANAGER UNIT TEST")
    print("=" * 60)

    manager = DataManager()

    print()

    print("Initial Cache :", manager.cache_size())

    candles = manager.get_candles(

        symbol="BTCUSDT",

        interval="1h",

        limit=5,

    )

    if candles is None:

        print("FAILED ❌")

        return

    print("After First Request :", manager.cache_size())

    manager.get_candles(

        symbol="BTCUSDT",

        interval="1h",

        limit=5,

    )

    print("After Second Request:", manager.cache_size())

    manager.clear_cache()

    print("After Clear Cache   :", manager.cache_size())

    print()

    if manager.cache_size() == 0:

        print("SUCCESS ✅")

    else:

        print("FAILED ❌")


if __name__ == "__main__":

    main()
