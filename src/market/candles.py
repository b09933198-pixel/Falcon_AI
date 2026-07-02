"""
Falcon AI

Market Layer

Candle Service

Version: 3.0.0
"""

from src.api.client import ToobitClient
from src.market.mapper import MarketMapper


class CandleService:

    def __init__(self):

        self.client = ToobitClient()

    def get_klines(

        self,

        symbol: str,

        interval: str = "1h",

        limit: int = 100,

    ):

        raw_data = self.client.get_klines(

            symbol=symbol,

            interval=interval,

            limit=limit,

        )

        if raw_data is None:

            return None

        candles = []

        for row in raw_data:

            candles.append(

                MarketMapper.to_candle(row)

            )

        return candles