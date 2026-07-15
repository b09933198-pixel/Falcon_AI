from .swing import Swing


class SwingBuilder:

    @staticmethod
    def high(

        index,

        price,

        strength=2,

        timeframe="Unknown",

        timestamp=0,

    ):

        return Swing(

            index=index,

            price=price,

            is_high=True,

            strength=strength,

            timeframe=timeframe,

            timestamp=timestamp,

        )

    @staticmethod
    def low(

        index,

        price,

        strength=2,

        timeframe="Unknown",

        timestamp=0,

    ):

        return Swing(

            index=index,

            price=price,

            is_high=False,

            strength=strength,

            timeframe=timeframe,

            timestamp=timestamp,

        )