from src.analysis.decision import Decision
from src.analysis.decision import DecisionType


def test_decision():

    d = Decision(

        action=DecisionType.BUY,

        confidence=0.92,

        score=0.88,

        reason="Bullish probability",

    )

    assert d.action == DecisionType.BUY

    assert d.confidence == 0.92