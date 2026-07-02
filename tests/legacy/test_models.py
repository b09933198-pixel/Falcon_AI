"""
Falcon AI

Model Layer Test

Tests:
- API Client
- CandleService
- Candle Model
"""

from src.market.candles import CandleService


def main():

    print("=" * 60)
    print("MODEL TEST")
    print("=" * 60)

    service = CandleService()

    candles = service.get_klines(
        symbol="BTCUSDT",
        interval="1h",
        limit=3
    )

    if candles is None:

        print("FAILED")
        return

    print("SUCCESS")
    print()

    print("Count :", len(candles))
    print()

    first = candles[0]

    print("TYPE :", type(first))
    print()

    print("Time   :", first.open_time)
    print("Open   :", first.open)
    print("High   :", first.high)
    print("Low    :", first.low)
    print("Close  :", first.close)
    print("Volume :", first.volume)

    print()

    print(first)


if __name__ == "__main__":
    main()