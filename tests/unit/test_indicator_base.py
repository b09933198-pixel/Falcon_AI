"""
Falcon AI

Enterprise Indicator Base Test

Version: 3.0.0
"""

import pytest

from src.analysis.indicators.base.indicator import Indicator


def test_indicator_is_abstract():
    with pytest.raises(TypeError):
        Indicator()