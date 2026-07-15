from src.analysis.risk import RiskBuilder


def test_builder():

    r = RiskBuilder.build(

        risk_percent=1.0,

        position_size=0.02,

        stop_loss=1800,

        take_profit=1840,

        risk_reward=2.0,

        max_loss=100,

        confidence=0.9,

        profile="MEDIUM",

    )

    assert r.position_size == 0.02

    assert r.profile == "MEDIUM"

    assert r.max_loss == 100