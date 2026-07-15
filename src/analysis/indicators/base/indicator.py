"""
Falcon AI

Enterprise Indicator Base

Version: 4.0.0
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Sequence

from src.domain.models import Candle


class Indicator(ABC):
    """
    Base contract for every analysis component.
    """

    name: str = "Indicator"
    category: str = "General"
    version: str = "4.0.0"
    description: str = ""
    ai_ready: bool = True

    @property
    def id(self) -> str:
        return self.__class__.__name__.lower()

    def validate(
        self,
        candles: Sequence[Candle],
        period: int,
    ) -> None:

        if period <= 0:
            raise ValueError(
                "period must be greater than zero"
            )

        if len(candles) < period:
            raise ValueError(
                "not enough candles"
            )

    @abstractmethod
    def calculate(
        self,
        candles: Sequence[Candle],
        period: int,
    ) -> list[float | None]:
        """
        Calculate indicator values.
        """
        raise NotImplementedError

    def metadata(self) -> dict:

        return {
            "id": self.id,
            "name": self.name,
            "category": self.category,
            "version": self.version,
            "description": self.description,
            "ai_ready": self.ai_ready,
        }

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}"
            f"(category={self.category})"
        )