"""
Falcon AI

Validation Layer

Forward-return test of a state signal

Version: 1.0.0

Question answered: when the analysis reports state S at the close of candle i,
what did price do afterwards? The result is a MEASUREMENT of a relationship.
It is not a strategy and it includes no fees or slippage.

Conventions
-----------
- Decision time: close of candle i.
- Entry: OPEN of candle i+1 (the first price obtainable after the decision).
- Exit: CLOSE of candle i+horizon.
- Returns are simple returns in basis points (1 bp = 0.01 %).
- Every sample stays inside one contiguous segment, so a data gap is never
  crossed by a forward return.
- States use only swings already confirmed at candle i (no lookahead).

Significance
------------
circular_shift_test compares the observed difference of mean forward return
between two states with the same difference after sliding the state series
against the return series by a random offset. The slide keeps the clustering
of states and the overlap of returns, and breaks only their relationship.
"""

from __future__ import annotations

import random
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Tuple

from src.analysis.smart_money import (
    StructureType,
    SwingDetectorEngine,
    structure_timeline,
)

_DETECTOR = SwingDetectorEngine()


@dataclass(frozen=True)
class Samples:
    states: List[StructureType]
    returns: List[float]
    timestamps: List[int]

    def __len__(self) -> int:
        return len(self.returns)


def forward_returns(candles: Sequence, horizon: int) -> List[Optional[float]]:
    """Forward return in bp per candle: open[i+1] -> close[i+horizon].

    None where the future is not fully available.
    """

    if not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon must be an integer >= 1")

    count = len(candles)
    out: List[Optional[float]] = [None] * count

    for i in range(count - horizon):

        entry = candles[i + 1].open

        if entry > 0:
            out[i] = (candles[i + horizon].close / entry - 1.0) * 10_000.0

    return out


def structure_states(
    candles: Sequence,
    strength: int,
    timeframe: str = "Unknown",
) -> List[StructureType]:
    """Market-structure trend knowable at the close of every candle."""

    swings = _DETECTOR.detect(candles, strength=strength, timeframe=timeframe)
    timeline = structure_timeline(swings)

    states: List[StructureType] = []
    pointer = 0
    current = StructureType.UNKNOWN

    for i in range(len(candles)):

        while pointer < len(timeline) and timeline[pointer][0] <= i:
            current = timeline[pointer][1]
            pointer += 1

        states.append(current)

    return states


def collect_samples(
    segments: Sequence[Sequence],
    strength: int,
    horizon: int,
    timeframe: str = "Unknown",
    states_cache: Optional[dict] = None,
) -> Samples:
    """(state, forward return) pairs from contiguous segments, in time order.

    states_cache may be a dict shared between calls: states depend only on
    (segment, strength), so they are reused across horizons.
    """

    states: List[StructureType] = []
    returns: List[float] = []
    timestamps: List[int] = []

    for number, segment in enumerate(segments):

        key = (number, strength)

        if states_cache is not None and key in states_cache:
            seg_states = states_cache[key]
        else:
            seg_states = structure_states(segment, strength, timeframe)
            if states_cache is not None:
                states_cache[key] = seg_states

        seg_returns = forward_returns(segment, horizon)

        for i, value in enumerate(seg_returns):

            if value is None:
                continue

            states.append(seg_states[i])
            returns.append(value)
            timestamps.append(segment[i + 1].timestamp)

    return Samples(states, returns, timestamps)


def group_means(
    states: Sequence,
    returns: Sequence[float],
    up,
    down,
) -> Tuple[int, int, float, float]:
    """(count_up, count_down, mean_up, mean_down). Means are nan when empty."""

    count_up = count_down = 0
    sum_up = sum_down = 0.0

    for state, value in zip(states, returns):

        if state == up:
            count_up += 1
            sum_up += value

        elif state == down:
            count_down += 1
            sum_down += value

    nan = float("nan")

    return (
        count_up,
        count_down,
        sum_up / count_up if count_up else nan,
        sum_down / count_down if count_down else nan,
    )


def signed_edge(states: Sequence, returns: Sequence[float], up, down) -> float:
    """Average return of a position that is long in `up` and short in `down`."""

    total = 0.0
    count = 0

    for state, value in zip(states, returns):

        if state == up:
            total += value
            count += 1

        elif state == down:
            total -= value
            count += 1

    return total / count if count else float("nan")


def circular_shift_test(
    states: Sequence,
    returns: Sequence[float],
    up,
    down,
    shifts: int = 1000,
    seed: int = 1,
    min_shift_fraction: float = 0.05,
) -> Tuple[float, float]:
    """(observed mean_up - mean_down, two-sided p-value).

    p = (hits + 1) / (shifts + 1), so it can never be exactly zero.
    """

    count = len(returns)

    if len(states) != count:
        raise ValueError("states and returns must have the same length")

    up_index = [i for i, s in enumerate(states) if s == up]
    down_index = [i for i, s in enumerate(states) if s == down]

    if not up_index or not down_index:
        raise ValueError("both states must occur at least once")

    low = max(1, int(count * min_shift_fraction))
    high = count - low

    if high < low:
        raise ValueError("series too short for the shift test")

    doubled = list(returns) + list(returns)
    n_up = len(up_index)
    n_down = len(down_index)

    def statistic(shift: int) -> float:
        total_up = sum(doubled[i + shift] for i in up_index)
        total_down = sum(doubled[i + shift] for i in down_index)
        return total_up / n_up - total_down / n_down

    observed = statistic(0)

    rng = random.Random(seed)
    hits = 0

    for _ in range(shifts):

        if abs(statistic(rng.randint(low, high))) >= abs(observed):
            hits += 1

    return observed, (hits + 1) / (shifts + 1)


def returns_by_year(
    timestamps: Sequence[int],
    states: Sequence,
    returns: Sequence[float],
    up,
    down,
    min_count: int = 30,
) -> Dict[int, Optional[float]]:
    """Per UTC year: mean_up - mean_down, or None when a state is too rare."""

    buckets: Dict[int, Tuple[list, list]] = {}

    for stamp, state, value in zip(timestamps, states, returns):

        year = datetime.fromtimestamp(stamp / 1000, tz=timezone.utc).year
        ups, downs = buckets.setdefault(year, ([], []))

        if state == up:
            ups.append(value)

        elif state == down:
            downs.append(value)

    result: Dict[int, Optional[float]] = {}

    for year, (ups, downs) in sorted(buckets.items()):

        if len(ups) < min_count or len(downs) < min_count:
            result[year] = None
        else:
            result[year] = sum(ups) / len(ups) - sum(downs) / len(downs)

    return result
