"""
Falcon AI

Core Domain Entity

Candle

Version: 4.0.0
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Candle:
    """
    Immutable OHLCV candle.

    Exchange-agnostic market data entity.
    """

    timestamp: int

    open: float
    high: float
    low: float
    close: float

    volume: float
    quote_volume: float

    trades: int

    buy_volume: float
    buy_quote_volume: float

    def __post_init__(self) -> None:

        if self.timestamp < 0:
            raise ValueError("timestamp must be >= 0")

        if self.open < 0:
            raise ValueError("open must be >= 0")

        if self.high < self.low:
            raise ValueError("high must be >= low")

        if not (self.low <= self.close <= self.high):
            raise ValueError(
                "close must be between low and high"
            )

        if self.volume < 0:
            raise ValueError("volume must be >= 0")

        if self.quote_volume < 0:
            raise ValueError(
                "quote_volume must be >= 0"
            )

        if self.trades < 0:
            raise ValueError("trades must be >= 0")

        if self.buy_volume < 0:
            raise ValueError(
                "buy_volume must be >= 0"
            )

        if self.buy_quote_volume < 0:
            raise ValueError(
                "buy_quote_volume must be >= 0"
            )

    @classmethod
    def from_api(cls, data: dict) -> "Candle":
        """
        Create Candle from normalized API data.
        """

        return cls(
            timestamp=int(data["timestamp"]),
            open=float(data["open"]),
            high=float(data["high"]),
            low=float(data["low"]),
            close=float(data["close"]),
            volume=float(data["volume"]),
            quote_volume=float(data["quote_volume"]),
            trades=int(data["trades"]),
            buy_volume=float(data["buy_volume"]),
            buy_quote_volume=float(
                data["buy_quote_volume"]
            ),
        )

    def to_dict(self) -> dict:

        return {
            "timestamp": self.timestamp,
            "open": self.open,
            "high": self.high,
            "low": self.low,
            "close": self.close,
            "volume": self.volume,
            "quote_volume": self.quote_volume,
            "trades": self.trades,
            "buy_volume": self.buy_volume,
            "buy_quote_volume": self.buy_quote_volume,
        }

    def __repr__(self) -> str:

        return (
            "Candle("
            f"time={self.timestamp}, "
            f"close={self.close}"
            ")"
        )