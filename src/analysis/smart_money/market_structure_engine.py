from .swing import Swing


class MarketStructureEngine:

    def __init__(self, swings: list[Swing]):

        self.swings = swings

    def highs(self):

        return [s for s in self.swings if s.is_high]

    def lows(self):

        return [s for s in self.swings if not s.is_high]

    def latest_high(self):

        highs = self.highs()

        return highs[-1] if highs else None

    def latest_low(self):

        lows = self.lows()

        return lows[-1] if lows else None