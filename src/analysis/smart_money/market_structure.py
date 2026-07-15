from dataclasses import dataclass

from .structure_type import StructureType


@dataclass(slots=True)
class MarketStructure:

    structure: StructureType

    strength: float

    confidence: float

    timeframe: str = "Unknown"

    timestamp: int = 0

    def as_dict(self):

        return {

            "structure": self.structure.value,

            "strength": self.strength,

            "confidence": self.confidence,

            "timeframe": self.timeframe,

            "timestamp": self.timestamp,

        }