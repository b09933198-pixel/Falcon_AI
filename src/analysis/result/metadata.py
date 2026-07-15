from dataclasses import dataclass


@dataclass(slots=True)
class AnalysisMetadata:

    symbol: str = ""

    timeframe: str = ""

    exchange: str = ""

    timestamp: int = 0

    model: str = "FalconAI"

    version: str = "5.0.0"

    def as_dict(self):

        return {

            "symbol": self.symbol,

            "timeframe": self.timeframe,

            "exchange": self.exchange,

            "timestamp": self.timestamp,

            "model": self.model,

            "version": self.version,

        }