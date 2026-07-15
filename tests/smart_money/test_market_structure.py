from src.analysis.smart_money import (
    MarketStructureBuilder,
    StructureType,
)


def test_market_structure():

    structure = MarketStructureBuilder.build(

        StructureType.BULLISH,

        strength=0.9,

        confidence=0.95,

    )

    assert structure.structure == StructureType.BULLISH

    assert structure.strength == 0.9

    assert structure.confidence == 0.95