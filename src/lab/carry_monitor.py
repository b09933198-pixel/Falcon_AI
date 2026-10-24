"""
Falcon AI

Lab

Funding-opportunity monitor (F-013 rule): reads the funding history of a symbol and says whether the
registered entry condition holds now. It is not a directional signal and not an instruction to trade.

Version: 1.0.0
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence, Tuple

DAY_MS = 86_400_000
COVERAGE_SLACK_MS = 12 * 3_600_000


def parse_history(payload) -> Tuple[List[int], List[float]]:
    """Toobit historyFundingRate rows [{"settleTime": "...", "settleRate": "..."}] -> ascending (times, rates)."""

    if not isinstance(payload, list):
        raise ValueError("funding history is not a list")

    rows = {}

    for row in payload:
        try:
            rows[int(row["settleTime"])] = float(row["settleRate"])
        except (KeyError, TypeError, ValueError):
            continue

    times = sorted(rows)

    return times, [rows[t] for t in times]


def daily_average(times: Sequence[int], rates: Sequence[float], now_ms: int, days: float) -> Optional[float]:
    """Sum of the rates of the events in (now - days, now] divided by days; None when the history does not cover the window."""

    start = now_ms - int(days * DAY_MS)

    if not times or times[0] > start + COVERAGE_SLACK_MS:
        return None

    return sum(r for t, r in zip(times, rates) if start < t <= now_ms) / days


def is_open(d_entry: Optional[float], entry_daily_rate: float) -> bool:
    return d_entry is not None and d_entry >= entry_daily_rate


def render_fa(now_text: str, rows: Sequence[Tuple[str, Optional[float], Optional[float], bool]],
              entry_daily_rate: float, entry_window_days: float) -> str:
    """rows: (symbol, average over the entry window, average over the exit window, open?)"""

    open_symbols = [r[0] for r in rows if r[3]]
    lines = [
        f"مانیتور تأمین مالی | {now_text} UTC",
        f"شرط ثبت‌شده‌ی ورود (F-013): میانگین {entry_window_days:g} روزه ≥ {entry_daily_rate * 100:.3f}٪ در روز",
        "فرصت فعال: " + ("، ".join(open_symbols) if open_symbols else "ندارد"),
        "",
    ]

    for symbol, d_in, d_out, opened in sorted(rows, key=lambda r: -(r[1] if r[1] is not None else -1.0)):
        if d_in is None:
            lines.append(f"{symbol}: داده‌ی کافی نیست")
            continue
        lines.append(f"{symbol}: {d_in * 100:.3f}٪ در روز (سالانه حدود {d_in * 365 * 100:.1f}٪ از مبلغ پوزیشن)"
                     + (" ← شرط برقرار" if opened else ""))

    lines += [
        "",
        "هشدارها:",
        "• جهت قیمت را نمی‌گوید و دستور معامله نیست؛ فقط می‌گوید شرط ثبت‌شده‌ی ورود الان برقرار است یا نه.",
        "• آزمون تاریخی فقط درآمد تأمین مالی را سنجید (داده‌ی Binance)، نه تفاوت قیمت اسپات و فیوچرز.",
        "• در معامله‌های تاریخی ۱۳٪ مواقع قیمت ≥۹۰٪ بالا رفت (لیکوئید شدن پای فروش با وثیقه‌ی ۱:۱).",
        "• سرمایه تقریباً ۷۶٪ زمان‌ها بیکار می‌ماند؛ بازده مؤثر بسیار کمتر از بازده زمان درگیری است.",
    ]

    return "\n".join(lines)
