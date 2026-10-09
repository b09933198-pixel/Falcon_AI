"""
Falcon AI Settings

All configurable values are defined here.
"""

# ==========================
# Exchange
# ==========================

EXCHANGE_NAME = "Toobit"

DEFAULT_TIMEFRAME = "1h"

DEFAULT_SYMBOLS = [
    "BTCUSDT",
    "ETHUSDT"
]

# ==========================
# Signal
# ==========================

MIN_CONFIDENCE_SCORE = 80

# ==========================
# Telegram
# ==========================

ENABLE_TELEGRAM = False

# ==========================
# Logging
# ==========================

ENABLE_LOGGING = True
# ==========================
# Market Scope
# ==========================
# Symbols and timeframes are configuration, never hard-coded.
# Any interval written as <number><unit> (15m, 1h, 4h, 1d, 1w) is supported.

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

SYMBOLS = list(DEFAULT_SYMBOLS)

TIMEFRAMES = {
    "15m": "entry",
    "1h": "structure",
    "4h": "direction",
    "1d": "direction",
}

# ==========================
# Historical Data
# ==========================

HISTORY_DB_PATH = PROJECT_ROOT / "data" / "history" / "history.db"
