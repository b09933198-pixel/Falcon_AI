"""
Falcon AI

Probability Rule Base

Version: 2.0.0
"""

from abc import ABC
from abc import abstractmethod


class ProbabilityRule(ABC):

    name = "Rule"

    weight = 1.0

    @abstractmethod
    def evaluate(
        self,
        features,
    ):
        pass