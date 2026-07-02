"""
Falcon AI

Indicator Base

Version: 2.0.0
"""

from abc import ABC, abstractmethod

from src.models import Candle


class Indicator(ABC):

    name = "Indicator"

    def validate(
        self,
        candles: list[Candle],
        period: int
    ):

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
        candles: list[Candle],
        period: int
    ) -> list[float | None]:
        pass