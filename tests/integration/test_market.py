"""
Falcon AI

Enterprise Market Integration Test

Version: 3.0.0
"""

from src.market.candles import CandleService
from src.domain.models import Candle


def test_market_layer_returns_enterprise_candles():
    service = CandleService()

    candles = service.get_klines(
        symbol="BTCUSDT",
        interval="1h",
        limit=5,
    )

    assert candles is not None
    assert len(candles) > 0

    first = candles[0]

    assert isinstance(first, Candle)

    assert first.high >= first.low
    assert first.low <= first.close <= first.high

    assert first.timestamp >= 0