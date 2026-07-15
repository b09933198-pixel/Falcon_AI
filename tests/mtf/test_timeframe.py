from src.analysis.mtf import Timeframe


def test_timeframe():

    assert Timeframe.M5.value == "5m"

    assert Timeframe.H1.value == "1h"

    assert Timeframe.D1.value == "1d"

    assert Timeframe.W1.value == "1w"