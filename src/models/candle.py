"""
Falcon AI

Module:
    Candle Model

Description:
    Internal OHLCV Candle Model

Version:
    2.0.0
"""


class Candle:

    def __init__(

        self,

        time,

        open,

        high,

        low,

        close,

        volume,

    ):

        self.time = int(time)

        self.open = float(open)

        self.high = float(high)

        self.low = float(low)

        self.close = float(close)

        self.volume = float(volume)

    def __repr__(self):

        return (

            "Candle("

            f"time={self.time}, "

            f"close={self.close}"

            ")"

        )