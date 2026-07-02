"""
Falcon AI

Market Mapper

Version:
    1.0.0
"""

from src.models.candle import Candle


class MarketMapper:

    @staticmethod
    def to_candle(data):

        return Candle(

            time=data[0],

            open=data[1],

            high=data[2],

            low=data[3],

            close=data[4],

            volume=data[5],

        )