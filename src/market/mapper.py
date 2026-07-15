"""
Falcon AI

Market Mapper

Version: 2.0.0
"""

from src.domain.models.candle import Candle


class MarketMapper:

    @staticmethod
    def to_candle(data):

        return Candle(
            timestamp=int(data[0]),
            open=float(data[1]),
            high=float(data[2]),
            low=float(data[3]),
            close=float(data[4]),
            volume=float(data[5]),
            quote_volume=float(data[7]),
            trades=int(data[8]),
            buy_volume=float(data[9]),
            buy_quote_volume=float(data[10]),
        )