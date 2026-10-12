"""
Falcon AI

Validation Layer

Positioning and order-flow signal scan

Version: 1.0.0

Turns derivatives data (funding rate, open interest, long/short ratios, taker
buy/sell volume) and the spot taker-buy share into the same +1 / -1 / 0 signals
that signal_scan.py evaluates, one value per candle.

Availability rules (no lookahead)
---------------------------------
The decision is taken at the close of candle i, that is at t = open_time + interval.
  funding   an event is known from its calc_time on.
  metrics   a 5-minute row stamped T is used only when T + 5 minutes <= t, because
            the archive does not say whether T marks the start or the end of the
            period. Rows older than a staleness limit are not used at all.
Percentile ranks use only the candles up to and including i.

Gaps are never filled: a feature is None when the data it needs is missing.
"""

from __future__ import annotations

import math
from bisect import bisect_left, bisect_right, insort
from collections import deque
from dataclasses import dataclass
from typing import Deque, List, Optional, Sequence, Tuple

from src.validation.signal_scan import Events

FIVE_MIN_MS = 300_000
HOUR_MS = 3_600_000


# ----------------------------------------------------------------------
# Data container
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class Positioning:
    """Time-sorted derivatives data for one symbol."""

    funding_ts: List[int]
    funding_rate: List[float]
    metric_ts: List[int]
    open_interest: List[Optional[float]]
    top_ls: List[Optional[float]]
    count_ls: List[Optional[float]]
    taker_ls: List[Optional[float]]

    @staticmethod
    def from_rows(funding_rows: Sequence[tuple], metric_rows: Sequence[tuple]) -> "Positioning":
        """funding rows (calc_time, interval_hours, rate); metric rows as DerivativesStore.metrics()."""

        funding = sorted(funding_rows, key=lambda r: r[0])
        metrics = sorted(metric_rows, key=lambda r: r[0])

        return Positioning(
            [r[0] for r in funding],
            [r[2] for r in funding],
            [r[0] for r in metrics],
            [r[1] for r in metrics],
            [r[4] for r in metrics],
            [r[5] for r in metrics],
            [r[6] for r in metrics],
        )


def _log_ratio(value: Optional[float]) -> Optional[float]:

    if value is None or value <= 0:
        return None

    return math.log(value)


# ----------------------------------------------------------------------
# Features (one value per candle, None when unavailable)
# ----------------------------------------------------------------------

def funding_feature(
    candles: Sequence,
    pos: Positioning,
    interval_ms: int = HOUR_MS,
    max_age_ms: int = 9 * HOUR_MS,
) -> List[Optional[float]]:
    """Latest funding rate known at the close of each candle."""

    out: List[Optional[float]] = []

    for candle in candles:

        t = candle.timestamp + interval_ms
        k = bisect_right(pos.funding_ts, t) - 1

        if k >= 0 and t - pos.funding_ts[k] <= max_age_ms:
            out.append(pos.funding_rate[k])
        else:
            out.append(None)

    return out


def _latest_metric(pos: Positioning, t: int, max_age_ms: int) -> Optional[int]:
    """Index of the newest metrics row usable at time t, or None."""

    k = bisect_right(pos.metric_ts, t - FIVE_MIN_MS) - 1

    if k < 0 or (t - FIVE_MIN_MS) - pos.metric_ts[k] > max_age_ms:
        return None

    return k


def open_interest_change_feature(
    candles: Sequence,
    pos: Positioning,
    interval_ms: int = HOUR_MS,
    hours: int = 24,
    max_age_ms: int = 30 * 60_000,
) -> List[Optional[float]]:
    """ln(open interest now / open interest `hours` ago)."""

    out: List[Optional[float]] = []

    for candle in candles:

        t = candle.timestamp + interval_ms
        now = _latest_metric(pos, t, max_age_ms)
        then = _latest_metric(pos, t - hours * HOUR_MS, max_age_ms)

        if now is None or then is None:
            out.append(None)
            continue

        a, b = pos.open_interest[now], pos.open_interest[then]

        out.append(math.log(a / b) if a and b and a > 0 and b > 0 else None)

    return out


def taker_flow_feature(
    candles: Sequence,
    pos: Positioning,
    interval_ms: int = HOUR_MS,
    hours: int = 4,
    min_share: float = 0.75,
) -> List[Optional[float]]:
    """Mean ln(taker buy / sell volume ratio) over the last `hours` of usable rows."""

    span = hours * HOUR_MS
    needed = int(min_share * span / FIVE_MIN_MS)
    out: List[Optional[float]] = []

    for candle in candles:

        t = candle.timestamp + interval_ms
        end = bisect_right(pos.metric_ts, t - FIVE_MIN_MS)
        start = bisect_right(pos.metric_ts, t - FIVE_MIN_MS - span)

        values = [v for v in (_log_ratio(x) for x in pos.taker_ls[start:end]) if v is not None]

        out.append(sum(values) / len(values) if len(values) >= needed else None)

    return out


def ratio_feature(
    candles: Sequence,
    pos: Positioning,
    column: str,
    interval_ms: int = HOUR_MS,
    max_age_ms: int = 30 * 60_000,
) -> List[Optional[float]]:
    """ln of the newest long/short ratio ('top_ls' or 'count_ls') usable at each close."""

    if column not in ("top_ls", "count_ls"):
        raise ValueError("column must be 'top_ls' or 'count_ls'")

    series = pos.top_ls if column == "top_ls" else pos.count_ls
    out: List[Optional[float]] = []

    for candle in candles:

        k = _latest_metric(pos, candle.timestamp + interval_ms, max_age_ms)
        out.append(_log_ratio(series[k]) if k is not None else None)

    return out


def spot_taker_feature(candles: Sequence, hours: int = 4, interval_ms: int = HOUR_MS) -> List[Optional[float]]:
    """Share of spot volume bought by takers over the last `hours`, from the candles themselves."""

    n = max(1, hours * HOUR_MS // interval_ms)
    out: List[Optional[float]] = []

    for i in range(len(candles)):

        if i + 1 < n:
            out.append(None)
            continue

        window = candles[i + 1 - n:i + 1]
        volume = sum(c.volume for c in window)

        out.append(sum(c.buy_volume for c in window) / volume if volume > 0 else None)

    return out


def past_return_sign(candles: Sequence, hours: int = 24, interval_ms: int = HOUR_MS) -> List[int]:
    """Sign of the close-to-close return over the last `hours` (0 when unknown or flat)."""

    n = max(1, hours * HOUR_MS // interval_ms)
    out: List[int] = []

    for i, candle in enumerate(candles):

        if i < n:
            out.append(0)
            continue

        change = candle.close - candles[i - n].close
        out.append((change > 0) - (change < 0))

    return out


# ----------------------------------------------------------------------
# Signals
# ----------------------------------------------------------------------

def percentile_signals(
    values: Sequence[Optional[float]],
    window: int = 2160,
    min_valid: int = 1000,
    high: float = 0.90,
    low: float = 0.10,
) -> List[int]:
    """+1 when a value ranks at or above `high` among the last `window` values
    (including itself), -1 when at or below `low`, else 0.

    Ties get their mid-rank, so a constant stretch never looks extreme.
    """

    if window < 2 or min_valid < 2 or min_valid > window or not 0 <= low < high <= 1:
        raise ValueError("invalid percentile parameters")

    recent: Deque[Optional[float]] = deque()
    ordered: List[float] = []
    out: List[int] = []

    for value in values:

        recent.append(value)

        if value is not None:
            insort(ordered, value)

        if len(recent) > window:
            oldest = recent.popleft()
            if oldest is not None:
                del ordered[bisect_left(ordered, oldest)]

        if value is None or len(ordered) < min_valid:
            out.append(0)
            continue

        rank = (bisect_left(ordered, value) + bisect_right(ordered, value)) / 2.0 / len(ordered)

        out.append(1 if rank >= high else -1 if rank <= low else 0)

    return out


def gated_direction(gate: Sequence[int], wanted: int, direction: Sequence[int]) -> List[int]:
    """direction[i] where gate[i] == wanted, else 0."""

    if len(gate) != len(direction):
        raise ValueError("series must have the same length")

    return [d if g == wanted else 0 for g, d in zip(gate, direction)]


# ----------------------------------------------------------------------
# Events split
# ----------------------------------------------------------------------

def split_events(events: Events, cutoff_ms: int, hold_ms: int) -> Tuple[Events, Events]:
    """(discovery, hold-out). Discovery keeps events whose whole holding period
    ended by the cutoff; hold-out keeps events decided at or after it."""

    first_t, first_e, second_t, second_e = [], [], [], []

    for stamp, edge in zip(events.timestamps, events.edges):

        if stamp + hold_ms <= cutoff_ms:
            first_t.append(stamp)
            first_e.append(edge)
        elif stamp >= cutoff_ms:
            second_t.append(stamp)
            second_e.append(edge)

    return Events(first_t, first_e), Events(second_t, second_e)
