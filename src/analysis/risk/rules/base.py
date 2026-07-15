"""
Falcon AI

Risk Rule Base

Version: 1.0.0
"""

from abc import ABC, abstractmethod

from ..context import RiskContext


class RiskRule(ABC):

    name = "Base"

    weight = 1.0

    @abstractmethod
    def evaluate(
        self,
        context: RiskContext,
    ):
        pass