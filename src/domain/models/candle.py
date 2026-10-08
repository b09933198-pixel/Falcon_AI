"""
Falcon AI

Core Domain Entity

Candle

Version: 5.0.0
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(slots=True, frozen=True)
class Candle:
    """
    Immutable, exchange-agnostic OHLCV market candle.

    This entity belongs to the Core Domain layer and must remain
    independent from exchanges, APIs, pandas, numpy, and storage.
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
        """Validate the domain invariants of the candle."""

        if self.timestamp < 0:
            raise ValueError("timestamp must be >= 0")

        if self.open < 0:
            raise ValueError("open must be >= 0")

        if self.high < 0:
            raise ValueError("high must be >= 0")

        if self.low < 0:
            raise ValueError("low must be >= 0")

        if self.close < 0:
            raise ValueError("close must be >= 0")

        if self.high < self.low:
            raise ValueError("high must be >= low")

        if not (self.low <= self.open <= self.high):
            raise ValueError(
                "open must be between low and high"
            )

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

        if self.buy_volume > self.volume:
            raise ValueError(
                "buy_volume must be <= volume"
            )

        if self.buy_quote_volume < 0:
            raise ValueError(
                "buy_quote_volume must be >= 0"
            )

        if self.buy_quote_volume > self.quote_volume:
            raise ValueError(
                "buy_quote_volume must be <= quote_volume"
            )

    @classmethod
    def from_api(cls, data: dict[str, Any]) -> "Candle":
        """
        Create a Candle from normalized API data.

        The API/infrastructure layer is responsible for normalizing
        exchange-specific responses before they reach this method.
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

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "Candle":
        """Create a Candle from a serialized dictionary."""

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

    def to_dict(self) -> dict[str, Any]:
        """Serialize the candle into a dictionary."""

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

    def to_tuple(self) -> tuple:
        """
        Serialize the candle into a stable positional tuple.

        Field order is intentionally identical to the dataclass
        declaration order.
        """

        return (
            self.timestamp,
            self.open,
            self.high,
            self.low,
            self.close,
            self.volume,
            self.quote_volume,
            self.trades,
            self.buy_volume,
            self.buy_quote_volume,
        )

    def __repr__(self) -> str:
        """Return a concise developer-friendly representation."""

        return (
            "Candle("
            f"time={self.timestamp}, "
            f"open={self.open}, "
            f"high={self.high}, "
            f"low={self.low}, "
            f"close={self.close}"
            ")"
        )
