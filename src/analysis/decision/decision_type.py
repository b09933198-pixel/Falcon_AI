from enum import Enum


class DecisionType(str, Enum):

    BUY = "BUY"

    SELL = "SELL"

    HOLD = "HOLD"

    WAIT = "WAIT"

    NO_TRADE = "NO_TRADE"