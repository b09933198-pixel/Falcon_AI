from src.analysis.risk.profile import RiskProfile


def test_profile():

    assert RiskProfile.LOW.value == "LOW"

    assert RiskProfile.MEDIUM.value == "MEDIUM"

    assert RiskProfile.HIGH.value == "HIGH"

    assert RiskProfile.AUTO.value == "AUTO"