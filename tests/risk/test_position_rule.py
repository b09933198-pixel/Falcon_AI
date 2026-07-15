from src.analysis.risk.rules import PositionSizeRule

from src.analysis.risk import (
    Account,
    RiskContext,
    RiskProfile,
)

from src.analysis.result import AnalysisResultBuilder
from src.analysis.features import FeatureVector
from src.analysis.probability import Probability
from src.analysis.reasoning import ReasonCollection


def test_position_rule():

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

    context = RiskContext(

        account=Account(

            balance=10000,

            equity=10000,

            free_margin=9800,

            leverage=20,

        ),

        analysis=analysis,

        profile=RiskProfile.MEDIUM,

    )

    size = PositionSizeRule().evaluate(

        context,

        stop_distance=100,

    )

    assert size == 1.0