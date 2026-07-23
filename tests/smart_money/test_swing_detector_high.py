from src.analysis.smart_money import SwingDetectorEngine
from src.domain.models import Candle


def candle(high: float, low: float):

    return Candle(

        timestamp=0,

        open=low,

        high=high,

        low=low,

        close=high,

        volume=0,

        quote_volume=0,

        trades=0,

        buy_volume=0,

        buy_quote_volume=0,

    )


def test_high():

    candles = [

        candle(10, 5),

        candle(12, 6),

        candle(15, 7),

        candle(20, 8),

        candle(30, 9),

        candle(18, 8),

        candle(15, 7),

        candle(12, 6),

        candle(10, 5),

    ]

    swings = SwingDetectorEngine().detect(candles)

    assert len(swings) == 1

    assert swings[0].is_high

    assert swings[0].price == 30