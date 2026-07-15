"""
Falcon AI

Multi Timeframe Weights

Version: 1.0.0
"""

from .timeframe import Timeframe


TIMEFRAME_WEIGHTS = {

    Timeframe.M5: 1,

    Timeframe.M15: 2,

    Timeframe.M30: 2,

    Timeframe.H1: 3,

    Timeframe.H4: 4,

    Timeframe.D1: 5,

    Timeframe.W1: 6,

    Timeframe.MN1: 7,

}