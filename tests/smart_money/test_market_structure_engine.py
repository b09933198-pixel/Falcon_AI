from src.analysis.smart_money import (
    MarketStructureEngine,
    SwingBuilder,
)


def test_market_structure_engine():

    swings = [

        SwingBuilder.high(index=1, price=100),

        SwingBuilder.low(index=2, price=90),

        SwingBuilder.high(index=3, price=110),

        SwingBuilder.low(index=4, price=95),

    ]

    engine = MarketStructureEngine(swings)

    assert len(engine.highs()) == 2

    assert len(engine.lows()) == 2

    assert engine.latest_high().price == 110

    assert engine.latest_low().price == 95