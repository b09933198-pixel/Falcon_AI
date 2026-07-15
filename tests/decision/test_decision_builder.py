from src.analysis.decision import DecisionBuilder
from src.analysis.decision import DecisionType


def test_builder():

    d = DecisionBuilder.build(

        action=DecisionType.BUY,

        confidence=0.90,

        score=0.85,

        reason="EMA Cross",

    )

    assert d.action == DecisionType.BUY

    assert d.score == 0.85