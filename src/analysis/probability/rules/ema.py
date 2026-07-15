"""
Falcon AI

EMA Probability Rule

Version: 2.0.0
"""

from src.analysis.features import FeatureVector
from src.analysis.probability.results import RuleResult
from src.analysis.reasoning import ReasonType

from .base import ProbabilityRule


class EMARule(ProbabilityRule):

    name = "EMA"

    def evaluate(
        self,
        features: FeatureVector,
    ) -> RuleResult:

        ema50 = features.get("EMA50")
        ema200 = features.get("EMA200")

        if ema50 is None or ema200 is None:

            return RuleResult(
                rule=self.name,
                bullish=0.33,
                bearish=0.33,
                neutral=0.34,
                confidence=0.0,
                reason_id="ema_missing",
                title="EMA Missing",
                description="EMA50 or EMA200 feature not available.",
                category=ReasonType.TREND,
                priority=99,
            )

        if ema50.value > ema200.value:

            bullish = 0.65
            bearish = 0.20
            neutral = 0.15
            confidence = 0.80

            reason_id = "ema_bullish"

            title = "EMA Bullish Cross"

            description = "EMA50 is above EMA200."

        elif ema50.value < ema200.value:

            bullish = 0.20
            bearish = 0.65
            neutral = 0.15
            confidence = 0.80

            reason_id = "ema_bearish"

            title = "EMA Bearish Cross"

            description = "EMA50 is below EMA200."

        else:

            bullish = 0.33
            bearish = 0.33
            neutral = 0.34
            confidence = 0.50

            reason_id = "ema_flat"

            title = "EMA Neutral"

            description = "EMA50 equals EMA200."

        return RuleResult(
            rule=self.name,
            bullish=bullish,
            bearish=bearish,
            neutral=neutral,
            confidence=confidence,
            reason_id=reason_id,
            title=title,
            description=description,
            category=ReasonType.TREND,
            priority=2,
        )