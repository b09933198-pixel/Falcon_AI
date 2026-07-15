from .market_structure import MarketStructure


class MarketStructureBuilder:

    @staticmethod
    def build(

        structure,

        strength,

        confidence,

        timeframe="Unknown",

        timestamp=0,

    ):

        return MarketStructure(

            structure,

            strength,

            confidence,

            timeframe,

            timestamp,

        )