"""
Falcon AI

Market Layer

Timeframe helpers

Converts interval strings such as "15m" or "4h" to milliseconds.
Any <number><unit> interval is accepted, so timeframes can be added
or removed through configuration without a code change.
"""

from __future__ import annotations

_UNIT_MS = {
    "s": 1_000,
    "m": 60_000,
    "h": 3_600_000,
    "d": 86_400_000,
    "w": 604_800_000,
}


def interval_to_ms(interval: str) -> int:
    """Return the length of an interval in milliseconds.

    Months ("1M") are not supported because their length varies.
    """

    if not isinstance(interval, str) or len(interval) < 2:
        raise ValueError(f"Unsupported interval: {interval!r}")

    amount, unit = interval[:-1], interval[-1]

    if unit not in _UNIT_MS or not amount.isdigit() or int(amount) <= 0:
        raise ValueError(f"Unsupported interval: {interval!r}")

    return int(amount) * _UNIT_MS[unit]
