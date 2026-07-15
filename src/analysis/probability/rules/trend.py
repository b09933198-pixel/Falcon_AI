"""
Falcon AI

Trend Probability Rule

Version: 2.0.0
"""

from src.analysis.features import FeatureVector
from src.analysis.probability.results import RuleResult
from src.analysis.reasoning import ReasonType

from .base import ProbabilityRule


class TrendRule(ProbabilityRule):

    name = "Trend"

    def evaluate(
        self,
        features: FeatureVector,
    ) -> RuleResult:

        ema50 = features.get("EMA50")
        ema200 = features.get("EMA200")

        sma50 = features.get("SMA50")
        sma200 = features.get("SMA200")

        score = 0

        if ema50 and ema200:

            if ema50.value > ema200.value:
                score += 1
            else:
                score -= 1

        if sma50 and sma200:

            if sma50.value > sma200.value:
                score += 1
            else:
                score -= 1

        if score >= 2:

            return RuleResult(
                rule=self.name,
                bullish=0.80,
                bearish=0.10,
                neutral=0.10,
                confidence=0.95,
                reason_id="trend_bullish",
                title="Bullish Trend",
                description="EMA and SMA confirm bullish trend.",
                category=ReasonType.TREND,
                priority=1,
            )

        if score <= -2:

            return RuleResult(
                rule=self.name,
                bullish=0.10,
                bearish=0.80,
                neutral=0.10,
                confidence=0.95,
                reason_id="trend_bearish",
                title="Bearish Trend",
                description="EMA and SMA confirm bearish trend.",
                category=ReasonType.TREND,
                priority=1,
            )

        return RuleResult(
            rule=self.name,
            bullish=0.40,
            bearish=0.30,
            neutral=0.30,
            confidence=0.60,
            reason_id="trend_neutral",
            title="Neutral Trend",
            description="Trend confirmation is weak.",
            category=ReasonType.TREND,
            priority=5,
        )