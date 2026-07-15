from src.analysis.smart_money import SwingBuilder


def test_swing():

    high = SwingBuilder.high(

        index=15,

        price=102.5,

    )

    low = SwingBuilder.low(

        index=20,

        price=98.2,

    )

    assert high.is_high is True

    assert low.is_high is False

    assert high.price == 102.5

    assert low.price == 98.2