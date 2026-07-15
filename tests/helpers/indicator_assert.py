"""
Falcon AI

Indicator Assert

Version: 1.0.0
"""


def assert_indicator(
    indicator,
    candles,
    expected,
    period,
):

    result = indicator.calculate(
        candles,
        period,
    )

    assert len(result) == len(expected)

    return result