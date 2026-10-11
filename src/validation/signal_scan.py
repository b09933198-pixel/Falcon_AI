"""
Falcon AI

Validation Layer

Price-action signal scan

Version: 1.0.0

Tests whether a rule-based price-action signal has a directional edge.

Every signal function returns one value per candle: +1 (expect up), -1 (expect
down) or 0 (no signal), computed ONLY from candles up to and including that
candle (swings only after they are confirmed). The decision is taken at the
close of candle i, the trade enters at the open of candle i+1 and leaves at the
close of candle i+horizon. Returns are in basis points, before fees.

Significance
------------
Block sign-flip test. Events are grouped into weekly blocks; the null
hypothesis "the signal's direction carries no information" is simulated by
flipping the sign of whole blocks at random. Event timing, volatility context
and the overlap of neighbouring forward windows are all kept; only the
relation between direction and outcome is broken.

No candle window crosses a data gap: signals are computed per contiguous
segment.
"""

from __future__ import annotations

import random
from bisect import bisect_left, bisect_right, insort
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from src.analysis.smart_money import StructureTracker, StructureType, SwingDetectorEngine
from src.domain.models import Candle
from src.validation.volatility_test import log_ranges, past_mean

_DETECTOR = SwingDetectorEngine()

HOUR_MS = 3_600_000
DAY_MS = 86_400_000
WEEK_MS = 7 * DAY_MS


# ----------------------------------------------------------------------
# Forward returns
# ----------------------------------------------------------------------

def forward_returns_bp(candles: Sequence, horizon: int) -> List[Optional[float]]:
    """Return in bp of entering at open[i+1] and leaving at close[i+horizon]."""

    if not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon must be an integer >= 1")

    n = len(candles)
    out: List[Optional[float]] = [None] * n

    for i in range(n - horizon):

        entry = candles[i + 1].open

        if entry > 0:
            out[i] = (candles[i + horizon].close / entry - 1.0) * 10_000.0

    return out


# ----------------------------------------------------------------------
# Resampling
# ----------------------------------------------------------------------

def resample(candles: Sequence, factor: int, interval_ms: int) -> Tuple[List[Candle], List[int]]:
    """Aggregate every `factor` aligned, contiguous candles into one.

    Returns (new candles, index in `candles` of the last candle of each group).
    Incomplete or misaligned groups are dropped, never filled.
    """

    if not isinstance(factor, int) or factor < 2:
        raise ValueError("factor must be an integer >= 2")

    if not isinstance(interval_ms, int) or interval_ms <= 0:
        raise ValueError("interval_ms must be a positive integer")

    span = factor * interval_ms
    out: List[Candle] = []
    last_index: List[int] = []
    i = 0
    n = len(candles)

    while i + factor <= n:

        if candles[i].timestamp % span != 0:
            i += 1
            continue

        group = candles[i:i + factor]

        if any(
            b.timestamp - a.timestamp != interval_ms for a, b in zip(group, group[1:])
        ):
            i += 1
            continue

        out.append(Candle(
            timestamp=group[0].timestamp,
            open=group[0].open,
            high=max(c.high for c in group),
            low=min(c.low for c in group),
            close=group[-1].close,
            volume=sum(c.volume for c in group),
            quote_volume=sum(c.quote_volume for c in group),
            trades=sum(c.trades for c in group),
            buy_volume=sum(c.buy_volume for c in group),
            buy_quote_volume=sum(c.buy_quote_volume for c in group),
        ))
        last_index.append(i + factor - 1)
        i += factor

    return out, last_index


# ----------------------------------------------------------------------
# Signals
# ----------------------------------------------------------------------

def hour_signals(candles: Sequence, hour: int) -> List[int]:
    """+1 on every candle that opens at `hour` (UTC); 0 elsewhere."""

    if not isinstance(hour, int) or not 0 <= hour <= 23:
        raise ValueError("hour must be an integer 0..23")

    return [1 if (c.timestamp % DAY_MS) // HOUR_MS == hour else 0 for c in candles]


def sweep_signals(candles: Sequence, strength: int, timeframe: str = "Unknown") -> List[int]:
    """Liquidity sweep: price pokes through the latest confirmed swing and closes back.

    +1  a candle's low goes below the latest confirmed swing low and it closes
        above that level (expect a bounce)
    -1  a candle's high goes above the latest confirmed swing high and it closes
        below that level (expect a drop)
    A swing counts only once: the first candle that trades through it consumes
    it, whether or not that candle closes back. A candle that sweeps both sides
    gives 0.
    """

    swings = _DETECTOR.detect(candles, strength=strength, timeframe=timeframe)

    latest: Dict[bool, object] = {True: None, False: None}
    used = set()
    pointer = 0
    out: List[int] = []

    for i, candle in enumerate(candles):

        while pointer < len(swings) and swings[pointer].confirmed_index <= i - 1:
            latest[swings[pointer].is_high] = swings[pointer]
            pointer += 1

        bull = bear = False

        low_swing = latest[False]
        if low_swing is not None and (False, low_swing.index) not in used and candle.low < low_swing.price:
            used.add((False, low_swing.index))
            bull = candle.close > low_swing.price

        high_swing = latest[True]
        if high_swing is not None and (True, high_swing.index) not in used and candle.high > high_swing.price:
            used.add((True, high_swing.index))
            bear = candle.close < high_swing.price

        out.append(1 if bull and not bear else -1 if bear and not bull else 0)

    return out


def breakout_signals(
    candles: Sequence,
    lookback: int = 24,
    vol_window: int = 24,
    history: int = 720,
    quantile: float = 0.20,
) -> List[int]:
    """Breakout out of a compression.

    Compression at candle j: the mean candle range of the last `vol_window`
    candles is within the lowest `quantile` of its own values over the last
    `history` candles (including j).
    Signal at candle i when compression held at i-1 and candle i CLOSES beyond
    the high (+1) or low (-1) of the previous `lookback` candles.
    """

    if lookback < 1 or vol_window < 1 or history < 2 or not 0 < quantile < 1:
        raise ValueError("invalid breakout parameters")

    n = len(candles)
    vol = past_mean(log_ranges(candles), vol_window)

    window: List[float] = []
    ordered: List[float] = []
    compressed = [False] * n

    for j in range(n):

        value = vol[j]

        if value is None:
            continue

        window.append(value)
        insort(ordered, value)

        if len(window) > history:
            oldest = window.pop(0)
            del ordered[bisect_left(ordered, oldest)]

        if len(window) == history:
            compressed[j] = bisect_right(ordered, value) / history <= quantile

    out = [0] * n

    for i in range(max(lookback, 1), n):

        if not compressed[i - 1]:
            continue

        prior = candles[i - lookback:i]
        high = max(c.high for c in prior)
        low = min(c.low for c in prior)

        if candles[i].close > high:
            out[i] = 1
        elif candles[i].close < low:
            out[i] = -1

    return out


def pullback_signals(
    candles: Sequence,
    interval_ms: int,
    ltf_strength: int = 5,
    htf_strength: int = 3,
    factor: int = 4,
) -> List[int]:
    """Pullback against the higher-timeframe trend.

    Higher timeframe = `factor` candles per bar, market-structure trend from
    confirmed swings of COMPLETED bars only.
      +1  higher timeframe BULLISH while the lower timeframe is BEARISH
      -1  higher timeframe BEARISH while the lower timeframe is BULLISH
    """

    htf, last_index = resample(candles, factor, interval_ms)

    ltf_swings = _DETECTOR.detect(candles, strength=ltf_strength, timeframe="LTF")
    htf_swings = _DETECTOR.detect(htf, strength=htf_strength, timeframe="HTF")

    ltf_tracker = StructureTracker()
    htf_tracker = StructureTracker()
    ltf_pointer = htf_pointer = done = 0
    out: List[int] = []

    for i in range(len(candles)):

        while done < len(htf) and last_index[done] <= i:
            done += 1

        while htf_pointer < len(htf_swings) and htf_swings[htf_pointer].confirmed_index <= done - 1:
            htf_tracker.update(htf_swings[htf_pointer])
            htf_pointer += 1

        while ltf_pointer < len(ltf_swings) and ltf_swings[ltf_pointer].confirmed_index <= i:
            ltf_tracker.update(ltf_swings[ltf_pointer])
            ltf_pointer += 1

        high_trend = htf_tracker.trend
        low_trend = ltf_tracker.trend

        if high_trend == StructureType.BULLISH and low_trend == StructureType.BEARISH:
            out.append(1)
        elif high_trend == StructureType.BEARISH and low_trend == StructureType.BULLISH:
            out.append(-1)
        else:
            out.append(0)

    return out


# ----------------------------------------------------------------------
# Events and statistics
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class Events:
    timestamps: List[int]
    edges: List[float]          # signal * forward return, bp

    def __len__(self) -> int:
        return len(self.edges)


def collect_events(
    segments: Sequence[Sequence],
    make_signals: Callable[[Sequence], List[int]],
    horizon: int,
) -> Events:
    """Every candle with a signal and a complete forward window."""

    stamps: List[int] = []
    edges: List[float] = []

    for segment in segments:

        signals = make_signals(segment)

        if len(signals) != len(segment):
            raise ValueError("a signal function must return one value per candle")

        returns = forward_returns_bp(segment, horizon)

        for candle, signal, ret in zip(segment, signals, returns):

            if signal != 0 and ret is not None:
                stamps.append(candle.timestamp)
                edges.append(signal * ret)

    return Events(stamps, edges)


def block_sign_flip_test(
    edges: Sequence[float],
    blocks: Sequence[int],
    flips: int = 2000,
    seed: int = 1,
) -> float:
    """Two-sided p-value of the summed edge under random sign flips of whole blocks."""

    if len(edges) != len(blocks):
        raise ValueError("edges and blocks must have the same length")

    totals: Dict[int, float] = {}

    for edge, block in zip(edges, blocks):
        totals[block] = totals.get(block, 0.0) + edge

    sums = list(totals.values())

    if len(sums) < 10:
        raise ValueError("need events in at least 10 blocks")

    observed = abs(sum(sums))
    rng = random.Random(seed)
    hits = 0

    for _ in range(flips):

        total = 0.0

        for s in sums:
            total += s if rng.random() < 0.5 else -s

        if abs(total) >= observed:
            hits += 1

    return (hits + 1) / (flips + 1)


@dataclass(frozen=True)
class SignalResult:
    events: int
    mean_edge: float
    hit_rate: float
    p_value: float
    years_same_sign: int
    years_usable: int


def evaluate_events(
    events: Events,
    flips: int = 2000,
    seed: int = 1,
    block_ms: int = WEEK_MS,
    min_year_events: int = 20,
) -> SignalResult:
    """Mean edge, significance and per-year consistency of a set of events."""

    n = len(events)

    if n < 30:
        raise ValueError("need at least 30 events")

    mean_edge = sum(events.edges) / n
    hit_rate = sum(1 for e in events.edges if e > 0) / n

    blocks = [stamp // block_ms for stamp in events.timestamps]
    p_value = block_sign_flip_test(events.edges, blocks, flips, seed)

    by_year: Dict[int, List[float]] = {}

    for stamp, edge in zip(events.timestamps, events.edges):
        year = datetime.fromtimestamp(stamp / 1000, tz=timezone.utc).year
        by_year.setdefault(year, []).append(edge)

    usable = [sum(v) / len(v) for v in by_year.values() if len(v) >= min_year_events]
    same = sum(1 for m in usable if m * mean_edge > 0)

    return SignalResult(n, mean_edge, hit_rate, p_value, same, len(usable))
