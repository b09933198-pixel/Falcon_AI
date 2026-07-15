from src.analysis.risk import (
    Account,
    RiskContext,
    RiskProfile,
    RiskEngine,
)

from src.analysis.result import AnalysisResultBuilder
from src.analysis.features import FeatureVector
from src.analysis.probability import Probability
from src.analysis.reasoning import ReasonCollection


def test_engine():

    analysis = AnalysisResultBuilder.build(

        features=FeatureVector(),

        probability=Probability(

            bullish=0.7,

            bearish=0.2,

            neutral=0.1,

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

        atr=50,

    )

    result = RiskEngine().evaluate(context)

    assert result.max_loss == 100

    assert result.stop_loss == 100

    assert result.take_profit == 200

    assert result.position_size == 1.0