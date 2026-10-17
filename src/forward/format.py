"""
Falcon AI

Forward Layer

Text of a risk sheet for a human reader (Persian, Telegram-ready)

Version: 1.0.0
"""

from __future__ import annotations

from datetime import datetime, timezone

from src.analysis.volatility.risksheet import Sheet

LEVEL_FA = {"low": "کم", "normal": "متوسط", "high": "بالا", "extreme": "بسیار بالا"}


def _price(value: float) -> str:

    return f"{value:,.0f}" if value >= 1000 else f"{value:,.2f}"


def format_sheet_fa(symbol: str, interval: str, sheet: Sheet, close_price: float, interval_ms: int) -> str:
    """Plain text; the amounts are the move from the entry price (about the last close)."""

    decision = datetime.fromtimestamp((sheet.decision_open_ms + interval_ms) / 1000, tz=timezone.utc)
    q = sheet.quantiles

    lines = [
        f"برگه‌ی ریسک {symbol} ({interval})",
        f"زمان: {decision:%Y-%m-%d %H:%M} UTC | قیمت: {_price(close_price)}",
        f"سطح ریسک: {LEVEL_FA[sheet.level]} (صدک {sheet.rank * 100:.0f} از یک سال اخیر)",
        f"دامنه‌ی مورد انتظار هر کندل در ۲۴ ساعت آینده: {sheet.expected_range * 100:.2f}٪",
        "بیشترین حرکت از قیمت ورود، در هر دو جهت، طی ۲۴ ساعت آینده:",
    ]

    for level in (0.5, 0.8, 0.95):
        lines.append(f"• با احتمال {level * 100:.0f}٪ بیشتر از {q[level] * 100:.2f}٪ (حدود {_price(close_price * q[level])}) نمی‌شود")

    lines.append("جهت قیمت پیش‌بینی نمی‌شود. عدد ۹۵٪ معتبرتر از ۸۰٪ است؛ اعتبار پیشرو هنوز در آزمون است (F-008).")

    return "\n".join(lines)
