"""
Falcon AI
Main Entry Point

Version : 2.0.0
"""

from config.constants import APP_NAME, VERSION

from config.settings import (
    EXCHANGE_NAME,
    DEFAULT_TIMEFRAME,
    DEFAULT_SYMBOLS
)

from src.api.client import ToobitClient
from src.utils.logger import Logger


def banner():

    print("=" * 40)
    print(f"        {APP_NAME}")
    print(" Intelligent Trading Analysis System")
    print(f" Version: {VERSION}")
    print("=" * 40)

    print(f"Exchange : {EXCHANGE_NAME}")
    print(f"Timeframe: {DEFAULT_TIMEFRAME}")
    print(f"Symbols  : {', '.join(DEFAULT_SYMBOLS)}")


def main():

    Logger.info(f"{APP_NAME} v{VERSION} started.")

    banner()

    Logger.info("Configuration loaded successfully.")

    client = ToobitClient()

    # -----------------------------
    # API Connection Test
    # -----------------------------

    if not client.ping():
        Logger.error("Cannot connect to Toobit API.")
        return

    Logger.info("Connected to Toobit API.")

    # -----------------------------
    # Get BTC Price
    # -----------------------------

    ticker = client.get_ticker("BTCUSDT")

    if ticker is None:

        Logger.error("Cannot get ticker price.")

    else:

        Logger.info(
            f"{ticker['symbol']} Price : {ticker['price']}"
        )

    Logger.info("System Started Successfully.")


if __name__ == "__main__":
    main()