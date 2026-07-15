"""
Falcon AI

Probability Engine

Version: 5.0.0
"""

from src.analysis.features import FeatureVector

from .probability import Probability
from .results import RuleResult
from .rules import RuleRegistry


class ProbabilityEngine:

    def __init__(self):

        self.registry = RuleRegistry()

    def calculate(
        self,
        features: FeatureVector,
    ) -> Probability:

        bullish = 0.0
        bearish = 0.0
        neutral = 0.0
        confidence = 0.0

        total_weight = 0.0

        timeframe = "Unknown"

        for rule in self.registry.all():

            result: RuleResult = rule.evaluate(features)

            weight = rule.weight

            bullish += result.bullish * weight
            bearish += result.bearish * weight
            neutral += result.neutral * weight
            confidence += result.confidence * weight

            total_weight += weight

            if result.timeframe != "Unknown":
                timeframe = result.timeframe

        if total_weight > 0:

            bullish /= total_weight
            bearish /= total_weight
            neutral /= total_weight
            confidence /= total_weight

        return Probability(

            bullish=bullish,

            bearish=bearish,

            neutral=neutral,

            confidence=confidence,

            model="WeightedRuleFusion",

            timeframe=timeframe,

        )