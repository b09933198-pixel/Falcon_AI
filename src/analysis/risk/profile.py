"""
Falcon AI

Risk Profile

Version: 1.0.0
"""

from enum import StrEnum


class RiskProfile(StrEnum):

    LOW = "LOW"

    MEDIUM = "MEDIUM"

    HIGH = "HIGH"

    AUTO = "AUTO"