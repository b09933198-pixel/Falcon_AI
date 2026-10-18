"""
Falcon AI

Strategy Lab

Indicators (docs/STRATEGIES_F009.md, common definitions)

Version: 1.0.0

Every function returns one value per input row. Value i uses only rows 0..i. None means "not enough rows yet".
"""

from __future__ import annotations

import math
from typing import List, Optional, Sequence, Tuple


def true_ranges(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float]) -> List[Optional[float]]:
    """True range; the first row has none (no previous close)."""

    out: List[Optional[float]] = [None]

    for i in range(1, len(closes)):
        out.append(max(highs[i] - lows[i], abs(highs[i] - closes[i - 1]), abs(lows[i] - closes[i - 1])))

    return out


def atr_wilder(highs: Sequence[float], lows: Sequence[float], closes: Sequence[float], n: int = 14) -> List[Optional[float]]:
    """Wilder ATR: first value at index n (mean of true ranges 1..n), then Wilder smoothing."""

    tr = true_ranges(highs, lows, closes)
    out: List[Optional[float]] = [None] * len(closes)

    if len(closes) <= n:
        return out

    value = sum(tr[1:n + 1]) / n
    out[n] = value

    for i in range(n + 1, len(closes)):
        value = (value * (n - 1) + tr[i]) / n
        out[i] = value

    return out


def rsi_wilder(closes: Sequence[float], n: int = 14) -> List[Optional[float]]:
    """Wilder RSI: first value at index n. No losses and no gains gives 50; no losses gives 100."""

    out: List[Optional[float]] = [None] * len(closes)

    if len(closes) <= n:
        return out

    gains = [max(closes[i] - closes[i - 1], 0.0) for i in range(1, len(closes))]
    losses = [max(closes[i - 1] - closes[i], 0.0) for i in range(1, len(closes))]
    avg_gain = sum(gains[:n]) / n
    avg_loss = sum(losses[:n]) / n

    def value() -> float:
        if avg_gain == 0 and avg_loss == 0:
            return 50.0
        if avg_loss == 0:
            return 100.0
        return 100.0 - 100.0 / (1.0 + avg_gain / avg_loss)

    out[n] = value()

    for i in range(n + 1, len(closes)):
        avg_gain = (avg_gain * (n - 1) + gains[i - 1]) / n
        avg_loss = (avg_loss * (n - 1) + losses[i - 1]) / n
        out[i] = value()

    return out


def sma(values: Sequence[float], n: int) -> List[Optional[float]]:

    out: List[Optional[float]] = [None] * len(values)
    total = 0.0

    for i, v in enumerate(values):
        total += v

        if i >= n:
            total -= values[i - n]

        if i >= n - 1:
            out[i] = total / n

    return out


def ema(values: Sequence[float], n: int) -> List[Optional[float]]:
    """EMA with alpha = 2/(n+1), seeded with the simple average of the first n values (value at index n-1)."""

    out: List[Optional[float]] = [None] * len(values)

    if len(values) < n:
        return out

    alpha = 2.0 / (n + 1)
    value = sum(values[:n]) / n
    out[n - 1] = value

    for i in range(n, len(values)):
        value = alpha * values[i] + (1 - alpha) * value
        out[i] = value

    return out


def bollinger(closes: Sequence[float], n: int = 20, k: float = 2.0) -> Tuple[List[Optional[float]], List[Optional[float]], List[Optional[float]], List[Optional[float]]]:
    """(mid, upper, lower, bandwidth) with population standard deviation; bandwidth = (upper - lower) / mid."""

    mid = sma(closes, n)
    upper: List[Optional[float]] = [None] * len(closes)
    lower: List[Optional[float]] = [None] * len(closes)
    width: List[Optional[float]] = [None] * len(closes)

    for i in range(n - 1, len(closes)):
        window = closes[i - n + 1:i + 1]
        std = math.sqrt(sum((x - mid[i]) ** 2 for x in window) / n)
        upper[i] = mid[i] + k * std
        lower[i] = mid[i] - k * std
        width[i] = (upper[i] - lower[i]) / mid[i] if mid[i] else None

    return mid, upper, lower, width


def pivot_highs(highs: Sequence[float], w: int = 5) -> List[int]:
    """Indexes k whose high is strictly greater than the w highs before and the w highs after.

    A pivot at k is known only at candle k + w; callers must respect that."""

    out: List[int] = []

    for k in range(w, len(highs) - w):
        if all(highs[k] > highs[k - j] and highs[k] > highs[k + j] for j in range(1, w + 1)):
            out.append(k)

    return out


def pivot_lows(lows: Sequence[float], w: int = 5) -> List[int]:

    out: List[int] = []

    for k in range(w, len(lows) - w):
        if all(lows[k] < lows[k - j] and lows[k] < lows[k + j] for j in range(1, w + 1)):
            out.append(k)

    return out
