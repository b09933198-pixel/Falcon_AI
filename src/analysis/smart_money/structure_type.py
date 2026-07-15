from enum import Enum


class StructureType(str, Enum):

    BULLISH = "Bullish"

    BEARISH = "Bearish"

    RANGING = "Ranging"

    UNKNOWN = "Unknown"