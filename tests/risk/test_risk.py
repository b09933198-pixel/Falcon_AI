from src.analysis.risk import RiskResult


def test_risk():

    result = RiskResult(

        risk_percent=1.0,

        position_size=0.02,

        stop_loss=1800,

        take_profit=1840,

        risk_reward=2.0,

        max_loss=100,

        confidence=0.90,

        profile="MEDIUM",

    )

    assert result.position_size == 0.02

    assert result.profile == "MEDIUM"

    assert result.risk_reward == 2.0