"""
Falcon AI

RSI Probability Rule

Version: 2.0.0
"""

from src.analysis.features import FeatureVector
from src.analysis.probability.results import RuleResult
from src.analysis.reasoning import ReasonType

from .base import ProbabilityRule


class RSIRule(ProbabilityRule):

    name = "RSI"

    def evaluate(
        self,
        features: FeatureVector,
    ) -> RuleResult:

        feature = features.get("RSI")

        if feature is None:

            return RuleResult(
                rule=self.name,
                bullish=0.33,
                bearish=0.33,
                neutral=0.34,
                confidence=0.0,
                reason_id="rsi_missing",
                title="RSI Missing",
                description="RSI feature not available.",
                category=ReasonType.MOMENTUM,
                priority=99,
            )

        value = feature.value

        if value < 30:

            bullish = 0.70
            bearish = 0.20
            neutral = 0.10
            confidence = 0.90

            description = "RSI indicates oversold market."

        elif value > 70:

            bullish = 0.20
            bearish = 0.70
            neutral = 0.10
            confidence = 0.90

            description = "RSI indicates overbought market."

        else:

            bullish = 0.30
            bearish = 0.30
            neutral = 0.40
            confidence = 0.60

            description = "RSI is neutral."

        return RuleResult(
            rule=self.name,
            bullish=bullish,
            bearish=bearish,
            neutral=neutral,
            confidence=confidence,
            reason_id="rsi_signal",
            title="RSI Signal",
            description=description,
            category=ReasonType.MOMENTUM,
            priority=2,
        )