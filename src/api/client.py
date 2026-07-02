"""
Falcon AI
API Client

Version: 2.2.0
"""

import requests


class ToobitClient:

    BASE_URL = "https://api.toobit.com"

    def __init__(self):
        self.session = requests.Session()

    def ping(self) -> bool:

        try:

            response = self.session.get(
                f"{self.BASE_URL}/api/v1/ping",
                timeout=10
            )

            return response.status_code == 200

        except requests.RequestException:

            return False

    def get_ticker(self, symbol: str):

        try:

            response = self.session.get(
                f"{self.BASE_URL}/quote/v1/ticker/price",
                params={
                    "symbol": symbol
                },
                timeout=10
            )

            if response.status_code != 200:
                return None

            data = response.json()

            if not isinstance(data, list):
                return None

            if len(data) == 0:
                return None

            ticker = data[0]

            return {
                "symbol": ticker["s"],
                "price": float(ticker["p"])
            }

        except (
            requests.RequestException,
            ValueError,
            KeyError,
            IndexError,
            TypeError
        ):

            return None

    def get_klines(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100
    ):

        try:

            response = self.session.get(
                f"{self.BASE_URL}/quote/v1/klines",
                params={
                    "symbol": symbol,
                    "interval": interval,
                    "limit": limit
                },
                timeout=10
            )

            if response.status_code != 200:
                return None

            return response.json()

        except requests.RequestException:

            return None