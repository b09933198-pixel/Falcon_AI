"""
Falcon AI

Reason Categories

Version: 1.0.0
"""

from enum import StrEnum


class ReasonType(StrEnum):

    TREND = "Trend"

    MOMENTUM = "Momentum"

    VOLATILITY = "Volatility"

    LIQUIDITY = "Liquidity"

    SMART_MONEY = "SmartMoney"

    VOLUME = "Volume"

    PATTERN = "Pattern"

    SESSION = "Session"

    RISK = "Risk"

    CONFIRMATION = "Confirmation"