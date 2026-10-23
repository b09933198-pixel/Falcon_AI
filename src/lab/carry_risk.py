"""
Falcon AI

Lab

F-013 exploratory diagnostic: how far did the spot price rise during each carry trade
(the loss of the short perpetual leg, as a fraction of the position size)

Version: 1.0.0
"""

from __future__ import annotations

from typing import Dict, Optional, Sequence

HOUR_MS = 3_600_000


def max_rise(candles: Sequence, entry_ms: int, exit_ms: int) -> Optional[float]:
    """Highest high during the trade divided by the open of the first candle at or after the entry, minus 1.

    None when there is no candle within one hour of the entry.
    """

    window = [c for c in candles if entry_ms <= c.timestamp < exit_ms]

    if not window or window[0].timestamp - entry_ms > HOUR_MS:
        return None

    return max(c.high for c in window) / window[0].open - 1.0


def quantile(sorted_values: Sequence[float], q: float) -> float:
    return sorted_values[min(len(sorted_values) - 1, int(q * len(sorted_values)))]


def summarize(rises: Sequence[float]) -> Dict[str, float]:
    values = sorted(rises)
    n = len(values)
    out: Dict[str, float] = {"n": n}

    if n == 0:
        return out

    out.update(median=quantile(values, 0.5), p90=quantile(values, 0.9), p99=quantile(values, 0.99), max=values[-1])

    for level in (0.3, 0.5, 0.9):
        out[f"share_ge_{int(level * 100)}"] = sum(1 for v in values if v >= level) / n

    return out
