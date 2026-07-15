from src.analysis.strategy import TradingPlanBuilder

from src.analysis.result import AnalysisResultBuilder
from src.analysis.features import FeatureVector
from src.analysis.probability import Probability
from src.analysis.reasoning import ReasonCollection

from src.analysis.decision import Decision, DecisionType
from src.analysis.risk import RiskResult


def test_trading_plan():

    analysis = AnalysisResultBuilder.build(

        features=FeatureVector(),

        probability=Probability(

            bullish=0.5,
            bearish=0.3,
            neutral=0.2,
            confidence=0.9,

        ),

        reasons=ReasonCollection(),

    )

    decision = Decision(

        action=DecisionType.BUY,

        confidence=0.9,

        score=0.8,

        reason="Probability favors buyers",

    )

    risk = RiskResult(

        risk_percent=1.0,

        position_size=1.0,

        stop_loss=100.0,

        take_profit=200.0,

        risk_reward=2.0,

        max_loss=100.0,

        confidence=0.9,

        profile="Balanced",

    )

    plan = TradingPlanBuilder.build(

        analysis=analysis,

        decision=decision,

        risk=risk,

    )

    assert plan.analysis is analysis

    assert plan.decision.action == DecisionType.BUY

    assert plan.risk.profile == "Balanced"