"""
Falcon AI

Validation Layer

Volatility forecast test

Version: 1.0.0

Two questions, answered by MEASUREMENT (no strategy, no fees):

  1. How much of the volatility of the next `horizon` candles can already be
     predicted from past volatility and the time of day?   (baseline model)
  2. Does a market-structure feature add information BEYOND that baseline?

Definitions
-----------
- Candle volatility: ln(high / low).
- Target y: ln(mean candle volatility over candles i+1 .. i+horizon).
- Baseline regressors, all knowable at the close of candle i:
    ln(mean candle volatility over the last `fast` candles),
    ln(mean candle volatility over the last `slow` candles),
    time of day as sin/cos of the 24h cycle (first and second harmonic).
- Structure features (swings used only after they are confirmed):
    leg      ln(size of the latest swing leg / close)
    age      ln(1 + candles since the latest swing was confirmed)
    ranging  1 when market structure is RANGING, else 0

Incremental information
-----------------------
Frisch-Waugh: the feature is residualised on the baseline, the target is
residualised on the baseline, and the correlation between the two residual
series is tested with a circular-shift test (see residual_shift_test). The
slide keeps the autocorrelation of both series, which overlapping targets
create, and breaks only their relationship.

Every sample stays inside one contiguous segment, so a data gap is never
crossed by a window.
"""

from __future__ import annotations

import math
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from operator import mul
from typing import Dict, List, Optional, Sequence, Tuple

from src.analysis.smart_money import (
    StructureTracker,
    StructureType,
    SwingDetectorEngine,
)

_DETECTOR = SwingDetectorEngine()

BASE_NAMES = ("vol_fast", "vol_slow", "sin1", "cos1", "sin2", "cos2")
FEATURE_NAMES = ("leg", "age", "ranging")

_FLOOR = 1e-6
_DAY_MS = 86_400_000


# ----------------------------------------------------------------------
# Rolling windows
# ----------------------------------------------------------------------

def log_ranges(candles: Sequence) -> List[float]:
    """ln(high / low) per candle (0.0 when the candle has no valid range)."""

    out: List[float] = []

    for c in candles:

        if c.low > 0 and c.high >= c.low:
            out.append(math.log(c.high / c.low))
        else:
            out.append(0.0)

    return out


def past_mean(values: Sequence[float], window: int) -> List[Optional[float]]:
    """Mean of values[i-window+1 .. i]; None until the window is full."""

    if not isinstance(window, int) or window < 1:
        raise ValueError("window must be an integer >= 1")

    out: List[Optional[float]] = [None] * len(values)
    total = 0.0

    for i, v in enumerate(values):

        total += v

        if i >= window:
            total -= values[i - window]

        if i >= window - 1:
            out[i] = total / window

    return out


def future_mean(values: Sequence[float], horizon: int) -> List[Optional[float]]:
    """Mean of values[i+1 .. i+horizon]; None where the future is incomplete."""

    if not isinstance(horizon, int) or horizon < 1:
        raise ValueError("horizon must be an integer >= 1")

    n = len(values)
    out: List[Optional[float]] = [None] * n

    if n <= horizon:
        return out

    total = sum(values[1:horizon + 1])
    out[0] = total / horizon

    for i in range(1, n - horizon):
        total += values[i + horizon] - values[i]
        out[i] = total / horizon

    return out


# ----------------------------------------------------------------------
# Structure features
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class StructureFeatures:
    leg: List[Optional[float]]
    age: List[Optional[float]]
    ranging: List[Optional[float]]


def structure_features(
    candles: Sequence,
    strength: int,
    timeframe: str = "Unknown",
) -> StructureFeatures:
    """Structure features knowable at the close of every candle."""

    swings = _DETECTOR.detect(candles, strength=strength, timeframe=timeframe)

    tracker = StructureTracker()
    pointer = 0
    last_confirmed: Optional[int] = None
    leg_size: Optional[float] = None
    ranging_now: Optional[float] = None

    leg: List[Optional[float]] = []
    age: List[Optional[float]] = []
    ranging: List[Optional[float]] = []

    for i, candle in enumerate(candles):

        updated = False

        while pointer < len(swings) and swings[pointer].confirmed_index <= i:
            tracker.update(swings[pointer])
            last_confirmed = swings[pointer].confirmed_index
            pointer += 1
            updated = True

        if updated:

            sequence = tracker.sequence

            if len(sequence) >= 2:
                leg_size = abs(sequence[-1].swing.price - sequence[-2].swing.price)

            trend = tracker.trend

            if trend == StructureType.UNKNOWN:
                ranging_now = None
            else:
                ranging_now = 1.0 if trend == StructureType.RANGING else 0.0

        if leg_size is not None and candle.close > 0:
            leg.append(math.log(max(leg_size / candle.close, _FLOOR)))
        else:
            leg.append(None)

        age.append(
            math.log(1.0 + (i - last_confirmed))
            if last_confirmed is not None
            else None
        )

        ranging.append(ranging_now)

    return StructureFeatures(leg, age, ranging)


# ----------------------------------------------------------------------
# Dataset
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class Dataset:
    y: List[float]
    columns: Dict[str, List[float]]
    timestamps: List[int]

    def __len__(self) -> int:
        return len(self.y)


def build_dataset(
    segments: Sequence[Sequence],
    strength: int,
    horizon: int,
    fast: int = 24,
    slow: int = 168,
    timeframe: str = "Unknown",
    features_cache: Optional[dict] = None,
) -> Dataset:
    """Aligned (target, baseline, structure features) rows in time order.

    A row exists only when every window is complete inside its segment and
    every structure feature is defined.
    """

    y: List[float] = []
    columns: Dict[str, List[float]] = {
        name: [] for name in BASE_NAMES + FEATURE_NAMES
    }
    timestamps: List[int] = []

    for number, segment in enumerate(segments):

        ranges = log_ranges(segment)
        fast_mean = past_mean(ranges, fast)
        slow_mean = past_mean(ranges, slow)
        ahead = future_mean(ranges, horizon)

        key = (number, strength)

        if features_cache is not None and key in features_cache:
            feats = features_cache[key]
        else:
            feats = structure_features(segment, strength, timeframe)
            if features_cache is not None:
                features_cache[key] = feats

        for i, candle in enumerate(segment):

            values = (
                fast_mean[i], slow_mean[i], ahead[i],
                feats.leg[i], feats.age[i], feats.ranging[i],
            )

            if any(v is None for v in values):
                continue

            angle = 2.0 * math.pi * (candle.timestamp % _DAY_MS) / _DAY_MS

            y.append(math.log(max(ahead[i], _FLOOR)))
            columns["vol_fast"].append(math.log(max(fast_mean[i], _FLOOR)))
            columns["vol_slow"].append(math.log(max(slow_mean[i], _FLOOR)))
            columns["sin1"].append(math.sin(angle))
            columns["cos1"].append(math.cos(angle))
            columns["sin2"].append(math.sin(2.0 * angle))
            columns["cos2"].append(math.cos(2.0 * angle))
            columns["leg"].append(feats.leg[i])
            columns["age"].append(feats.age[i])
            columns["ranging"].append(feats.ranging[i])
            timestamps.append(candle.timestamp)

    return Dataset(y, columns, timestamps)


# ----------------------------------------------------------------------
# Least squares
# ----------------------------------------------------------------------

def _solve(matrix: List[List[float]], vector: List[float]) -> List[float]:
    """Gaussian elimination with partial pivoting."""

    k = len(vector)
    a = [row[:] + [vector[i]] for i, row in enumerate(matrix)]

    for col in range(k):

        pivot = max(range(col, k), key=lambda r: abs(a[r][col]))

        if abs(a[pivot][col]) < 1e-9:
            raise ValueError("regressors are collinear (singular system)")

        a[col], a[pivot] = a[pivot], a[col]

        for r in range(col + 1, k):

            factor = a[r][col] / a[col][col]

            if factor:
                for c in range(col, k + 1):
                    a[r][c] -= factor * a[col][c]

    solution = [0.0] * k

    for i in range(k - 1, -1, -1):

        total = a[i][k] - sum(a[i][j] * solution[j] for j in range(i + 1, k))
        solution[i] = total / a[i][i]

    return solution


def ols_fit(columns: Sequence[Sequence[float]], y: Sequence[float]) -> List[float]:
    """[intercept, b1, ..., bk] by least squares (centred normal equations)."""

    k = len(columns)
    n = len(y)

    if k < 1:
        raise ValueError("at least one regressor is required")

    if any(len(c) != n for c in columns):
        raise ValueError("every column must have the same length as y")

    if n < k + 2:
        raise ValueError("not enough samples")

    means = [sum(c) / n for c in columns]
    y_mean = sum(y) / n

    centred = [[v - m for v in c] for c, m in zip(columns, means)]
    y_centred = [v - y_mean for v in y]

    a = [[0.0] * k for _ in range(k)]
    b = [0.0] * k

    for i in range(k):

        b[i] = sum(map(mul, centred[i], y_centred))

        for j in range(i, k):
            a[i][j] = a[j][i] = sum(map(mul, centred[i], centred[j]))

    coefficients = _solve(a, b)
    intercept = y_mean - sum(c * m for c, m in zip(coefficients, means))

    return [intercept] + coefficients


def ols_predict(coefficients: Sequence[float], columns: Sequence[Sequence[float]]) -> List[float]:

    if len(coefficients) != len(columns) + 1:
        raise ValueError("coefficients do not match the number of columns")

    out = [coefficients[0]] * len(columns[0])

    for coef, column in zip(coefficients[1:], columns):
        out = [o + coef * v for o, v in zip(out, column)]

    return out


def r_squared(y: Sequence[float], predicted: Sequence[float]) -> float:
    """1 - SSE / SST around the mean of y (can be negative out of sample)."""

    mean = sum(y) / len(y)
    sst = sum((v - mean) ** 2 for v in y)

    if sst == 0:
        return float("nan")

    sse = sum((v - p) ** 2 for v, p in zip(y, predicted))

    return 1.0 - sse / sst


def residuals(columns: Sequence[Sequence[float]], y: Sequence[float]) -> List[float]:

    fit = ols_fit(columns, y)
    predicted = ols_predict(fit, columns)

    return [v - p for v, p in zip(y, predicted)]


# ----------------------------------------------------------------------
# Significance and consistency
# ----------------------------------------------------------------------

def residual_shift_test(
    a: Sequence[float],
    b: Sequence[float],
    shifts: int = 1000,
    seed: int = 1,
    min_shift_fraction: float = 0.05,
) -> Tuple[float, float]:
    """(correlation of a and b, two-sided p-value) by circular shifting a.

    p = (hits + 1) / (shifts + 1), so it can never be exactly zero.
    """

    n = len(a)

    if len(b) != n:
        raise ValueError("series must have the same length")

    low = max(1, int(n * min_shift_fraction))
    high = n - low

    if n < 20 or high < low:
        raise ValueError("series too short for the shift test")

    norm = math.sqrt(sum(map(mul, a, a)) * sum(map(mul, b, b)))

    if norm == 0:
        raise ValueError("constant series")

    doubled = list(a) + list(a)
    observed = sum(map(mul, a, b)) / norm

    rng = random.Random(seed)
    hits = 0

    for _ in range(shifts):

        shift = rng.randint(low, high)
        value = sum(map(mul, doubled[shift:shift + n], b)) / norm

        if abs(value) >= abs(observed):
            hits += 1

    return observed, (hits + 1) / (shifts + 1)


def correlation_by_year(
    timestamps: Sequence[int],
    a: Sequence[float],
    b: Sequence[float],
    min_count: int = 500,
) -> Dict[int, Optional[float]]:
    """Per UTC year: correlation of a and b, or None when the year is too short."""

    buckets: Dict[int, Tuple[list, list]] = {}

    for stamp, x, z in zip(timestamps, a, b):

        year = datetime.fromtimestamp(stamp / 1000, tz=timezone.utc).year
        xs, zs = buckets.setdefault(year, ([], []))
        xs.append(x)
        zs.append(z)

    result: Dict[int, Optional[float]] = {}

    for year, (xs, zs) in sorted(buckets.items()):

        if len(xs) < min_count:
            result[year] = None
            continue

        norm = math.sqrt(sum(map(mul, xs, xs)) * sum(map(mul, zs, zs)))
        result[year] = sum(map(mul, xs, zs)) / norm if norm else None

    return result


def out_of_sample_r2(
    base_columns: Sequence[Sequence[float]],
    extra_columns: Sequence[Sequence[float]],
    y: Sequence[float],
    train_fraction: float = 0.7,
) -> Tuple[float, float]:
    """(R2 of the baseline, R2 of baseline + extra) on the LAST part of the data.

    Both models are fitted on the first `train_fraction` only.
    """

    split = int(len(y) * train_fraction)

    if split < len(base_columns) + len(extra_columns) + 2 or len(y) - split < 10:
        raise ValueError("not enough samples for an out-of-sample split")

    def part(columns, lo, hi):
        return [c[lo:hi] for c in columns]

    train_y, test_y = list(y[:split]), list(y[split:])

    base_fit = ols_fit(part(base_columns, 0, split), train_y)
    base_r2 = r_squared(test_y, ols_predict(base_fit, part(base_columns, split, len(y))))

    full = list(base_columns) + list(extra_columns)
    full_fit = ols_fit(part(full, 0, split), train_y)
    full_r2 = r_squared(test_y, ols_predict(full_fit, part(full, split, len(y))))

    return base_r2, full_r2


# ----------------------------------------------------------------------
# One feature, end to end
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class FeatureResult:
    name: str
    correlation: float
    p_value: float
    years_same_sign: int
    years_usable: int
    oos_gain: float


def baseline_columns(dataset: Dataset) -> List[List[float]]:

    return [dataset.columns[name] for name in BASE_NAMES]


def baseline_report(dataset: Dataset) -> Tuple[float, float]:
    """(in-sample R2, out-of-sample R2) of the baseline model."""

    base = baseline_columns(dataset)
    fit = ols_fit(base, dataset.y)
    in_sample = r_squared(dataset.y, ols_predict(fit, base))
    out_sample, _ = out_of_sample_r2(base, [], dataset.y)

    return in_sample, out_sample


def analyze_feature(
    dataset: Dataset,
    name: str,
    shifts: int = 1000,
    seed: int = 1,
) -> FeatureResult:
    """Incremental information of one structure feature beyond the baseline."""

    base = baseline_columns(dataset)
    feature = dataset.columns[name]

    ry = residuals(base, dataset.y)
    rz = residuals(base, feature)

    if sum(map(mul, rz, rz)) < 1e-12:
        return FeatureResult(name, float("nan"), 1.0, 0, 0, 0.0)

    correlation, p_value = residual_shift_test(rz, ry, shifts=shifts, seed=seed)

    by_year = correlation_by_year(dataset.timestamps, rz, ry)
    usable = [v for v in by_year.values() if v is not None]
    same = sum(1 for v in usable if v * correlation > 0)

    base_r2, full_r2 = out_of_sample_r2(base, [feature], dataset.y)

    return FeatureResult(name, correlation, p_value, same, len(usable), full_r2 - base_r2)
