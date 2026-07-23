"""
Falcon AI

Enterprise Data Layer Integration Test

Version: 3.0.0
"""

from src.data import DataManager
from src.domain.models import Candle


def test_data_layer_returns_enterprise_candles():
    manager = DataManager()

    candles = manager.get_candles(
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