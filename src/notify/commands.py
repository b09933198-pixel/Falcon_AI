"""
Falcon AI

Notify

Telegram command parsing and the help text

Version: 1.0.0
"""

from __future__ import annotations

from typing import Optional

HELP_FA = "\n".join([
    "دستورهای فالکون:",
    "/sheet برگه‌ی ریسک فعلی (BTC و ETH)",
    "/status آخرین اجرای ثبت روزانه",
    "/report گزارش آزمون زنده‌ی برگه‌ی ریسک (F-008)",
    "/carry مانیتور فرصت تأمین مالی",
    "/excel فایل‌های CSV برگه‌ها (در Excel باز می‌شوند)",
    "/help همین فهرست",
    "",
    "فالکون سیگنال خرید و فروش نمی‌دهد: هیچ قاعده‌ی جهت‌داری از آزمون‌ها نگذشت.",
])


def parse_command(text: Optional[str]) -> Optional[str]:
    """'/Sheet@bot now' -> 'sheet'; None when the text is not a command."""

    if not text or not text.strip():
        return None

    first = text.strip().split()[0]

    if not first.startswith("/"):
        return None

    return first[1:].split("@")[0].lower() or None
