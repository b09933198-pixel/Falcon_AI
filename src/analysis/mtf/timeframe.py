from enum import Enum


class Timeframe(Enum):
    M1 = "1m"
    M5 = "5m"
    M15 = "15m"
    M30 = "30m"

    H1 = "1h"
    H4 = "4h"

    D1 = "1d"

    W1 = "1w"

    MN1 = "1M"