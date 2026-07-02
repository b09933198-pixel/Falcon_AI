"""
Falcon AI Logger
"""

from datetime import datetime


class Logger:
    """Simple logger for Falcon AI."""

    @staticmethod
    def info(message: str) -> None:
        print(f"[INFO] {datetime.now()} | {message}")

    @staticmethod
    def warning(message: str) -> None:
        print(f"[WARNING] {datetime.now()} | {message}")

    @staticmethod
    def error(message: str) -> None:
        print(f"[ERROR] {datetime.now()} | {message}")