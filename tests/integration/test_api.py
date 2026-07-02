"""
Falcon AI

Standalone Toobit API Test

This file is NOT part of Falcon AI.
It is only used to verify API connectivity.
"""

import requests


BASE_URL = "https://api.toobit.com"


def test_ping():

    print("=" * 50)
    print("PING TEST")
    print("=" * 50)

    try:

        response = requests.get(
            f"{BASE_URL}/api/v1/ping",
            timeout=10
        )

        print("STATUS :", response.status_code)
        print("BODY   :", response.text)

    except Exception as e:

        print("PING ERROR")
        print(e)


def test_ticker():

    print()
    print("=" * 50)
    print("TICKER TEST")
    print("=" * 50)

    try:

        response = requests.get(
            f"{BASE_URL}/quote/v1/ticker/price",
            params={
                "symbol": "BTCUSDT"
            },
            timeout=10
        )

        print("URL    :", response.url)
        print("STATUS :", response.status_code)
        print("BODY   :", response.text)

        if response.status_code == 200:

            data = response.json()

            print()
            print("JSON TYPE :", type(data))
            print("JSON DATA :", data)

    except Exception as e:

        print("TICKER ERROR")
        print(e)


if __name__ == "__main__":

    test_ping()
    test_ticker()