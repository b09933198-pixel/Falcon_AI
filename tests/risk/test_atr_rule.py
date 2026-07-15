from src.analysis.risk import (
    Account,
    RiskContext,
    RiskProfile,
)

from src.analysis.risk.rules import ATRRule

from src.analysis.result import AnalysisResultBuilder
from src.analysis.features import FeatureVector
from src.analysis.probability import Probability
from src.analysis.reasoning import ReasonCollection


def test_atr_rule():

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

        atr=40,

    )

    stop = ATRRule().evaluate(context)

    assert stop == 80