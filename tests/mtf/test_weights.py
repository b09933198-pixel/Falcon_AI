from src.analysis.mtf import (
    Timeframe,
    TIMEFRAME_WEIGHTS,
)


def test_weights():

    assert TIMEFRAME_WEIGHTS[Timeframe.M5] == 1

    assert TIMEFRAME_WEIGHTS[Timeframe.H1] == 3

    assert TIMEFRAME_WEIGHTS[Timeframe.H4] == 4

    assert TIMEFRAME_WEIGHTS[Timeframe.D1] == 5

    assert TIMEFRAME_WEIGHTS[Timeframe.W1] == 6

    assert TIMEFRAME_WEIGHTS[Timeframe.MN1] == 7