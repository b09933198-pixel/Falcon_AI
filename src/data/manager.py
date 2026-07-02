"""
Falcon AI

Data Layer

Data Manager

Version: 2.0.0
"""

from src.market.candles import CandleService


class DataManager:

    def __init__(self):

        self.candle_service = CandleService()

    def get_candles(
        self,
        symbol: str,
        interval: str = "1h",
        limit: int = 100
    ):

        return self.candle_service.get_klines(
            symbol=symbol,
            interval=interval,
            limit=limit
        )