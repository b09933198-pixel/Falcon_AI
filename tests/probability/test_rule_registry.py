"""
Falcon AI

Rule Registry Tests

Version: 1.0.0
"""

from src.analysis.probability.rules import RuleRegistry


def test_registry_not_empty():

    registry = RuleRegistry()

    assert len(registry.all()) > 0


def test_registry_contains_rsi():

    registry = RuleRegistry()

    names = [
        type(rule).__name__
        for rule in registry.all()
    ]

    assert "RSIRule" in names


def test_registry_contains_ema():

    registry = RuleRegistry()

    names = [
        type(rule).__name__
        for rule in registry.all()
    ]

    assert "EMARule" in names


def test_registry_contains_trend():

    registry = RuleRegistry()

    names = [
        type(rule).__name__
        for rule in registry.all()
    ]

    assert "TrendRule" in names