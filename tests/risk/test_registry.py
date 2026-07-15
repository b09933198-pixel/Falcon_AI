from src.analysis.risk.rules import RiskRuleRegistry


def test_registry():

    registry = RiskRuleRegistry()

    assert len(registry.all()) > 0

    assert registry.all()[0].name == "ATR"