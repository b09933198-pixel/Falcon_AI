"""
Falcon AI

Standalone Toobit Candles Test

This file is NOT part of Falcon AI.
It is only used to verify Kline endpoint.
"""

import requests

BASE_URL = "https://api.toobit.com"


def test_candles():

    print("=" * 60)
    print("TOOBIT KLINE TEST")
    print("=" * 60)

    try:

        response = requests.get(
            f"{BASE_URL}/quote/v1/klines",
            params={
                "symbol": "BTCUSDT",
                "interval": "1h",
                "limit": 5
            },
            timeout=10
        )

        print("URL    :", response.url)
        print("STATUS :", response.status_code)
        print("BODY   :")
        print(response.text)

        if response.status_code == 200:

            data = response.json()

            print()
            print("TYPE :", type(data))
            print("COUNT:", len(data))

            if len(data) > 0:

                print()
                print("FIRST CANDLE")
                print(data[0])

    except Exception as e:

        print("ERROR :", repr(e))


if __name__ == "__main__":
    test_candles()