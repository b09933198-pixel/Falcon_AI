"""
Falcon AI

Analysis Layer

Adverse-excursion quantiles (risk sheet)

Version: 1.0.0

Answers: "how far can price move away from the next candle's open, in EITHER
direction, during the next `horizon` candles?"

    E = max(max(high[i+1..i+h]) - open[i+1], open[i+1] - min(low[i+1..i+h])) / open[i+1]

The quantiles of E are the volatility forecast (src/analysis/volatility) times
the empirical quantile of  E / expected_range  measured on training data only.
Nothing here forecasts direction.

The pre-registered claims and criteria are in research/FINDINGS.md (F-006).
"""

from __future__ import annotations

import math
from bisect import bisect_left, bisect_right, insort
from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, List, Optional, Sequence

from src.analysis.volatility.forecaster import VolatilityError, VolatilityForecaster, _quantile
from src.validation.volatility_test import future_mean, log_ranges, past_mean

QUANTILES = (0.50, 0.80, 0.95)

RISK_LEVELS = ("low", "normal", "high", "extreme")
RISK_BOUNDS = (0.25, 0.75, 0.95)          # percentile ranks that separate the levels


def excursion_targets(
    segments: Sequence[Sequence],
    horizon: int = 24,
    fast: int = 24,
    slow: int = 168,
) -> List[float]:
    """E for every row that `build_table` would create (same rows, same order)."""

    out: List[float] = []

    for segment in segments:

        ranges = log_ranges(segment)
        fast_mean = past_mean(ranges, fast)
        slow_mean = past_mean(ranges, slow)
        ahead = future_mean(ranges, horizon)

        for i in range(len(segment)):

            if fast_mean[i] is None or slow_mean[i] is None or ahead[i] is None:
                continue

            entry = segment[i + 1].open
            window = segment[i + 1:i + 1 + horizon]
            high = max(c.high for c in window)
            low = min(c.low for c in window)

            out.append(max(high - entry, entry - low) / entry)

    return out


def ratio_quantiles(
    excursions: Sequence[float],
    expected: Sequence[float],
    quantiles: Sequence[float] = QUANTILES,
) -> List[float]:
    """Empirical quantiles of E / expected_range."""

    if len(excursions) != len(expected) or len(excursions) < 200:
        raise VolatilityError("need at least 200 paired training rows")

    ratios = sorted(e / x for e, x in zip(excursions, expected) if x > 0)

    return [_quantile(ratios, q) for q in quantiles]


def trailing_ranks(
    values: Sequence[Optional[float]],
    window: int = 8760,
    min_valid: int = 2000,
) -> List[Optional[float]]:
    """Mid-rank (0..1) of each value among the last `window` values including itself.

    None until `min_valid` values are available. Uses only the past and the present.
    """

    if window < 2 or min_valid < 2 or min_valid > window:
        raise ValueError("invalid window parameters")

    recent: Deque[Optional[float]] = deque()
    ordered: List[float] = []
    out: List[Optional[float]] = []

    for value in values:

        recent.append(value)

        if value is not None:
            insort(ordered, value)

        if len(recent) > window:
            oldest = recent.popleft()
            if oldest is not None:
                del ordered[bisect_left(ordered, oldest)]

        if value is None or len(ordered) < min_valid:
            out.append(None)
            continue

        out.append((bisect_left(ordered, value) + bisect_right(ordered, value)) / 2.0 / len(ordered))

    return out


def risk_level(rank: float) -> str:
    """low (< 25 %), normal (25-75 %), high (75-95 %), extreme (>= 95 %)."""

    if not 0.0 <= rank <= 1.0:
        raise ValueError("rank must be in [0, 1]")

    for name, bound in zip(RISK_LEVELS, RISK_BOUNDS):
        if rank < bound:
            return name

    return RISK_LEVELS[-1]


@dataclass(frozen=True)
class RiskSheet:
    """What the analyst reports at one candle close."""

    expected_range: float
    upper_range: float
    quantiles: Dict[float, float]          # {0.5: ..., 0.8: ..., 0.95: ...} as fractions of price


class ExcursionModel:
    """Volatility forecaster plus excursion quantiles."""

    def __init__(self, interval_ms: int, horizon: int = 24, quantiles: Sequence[float] = QUANTILES):

        self.volatility = VolatilityForecaster(interval_ms=interval_ms, horizon=horizon)
        self.horizon = horizon
        self.quantile_levels = tuple(quantiles)
        self.ratio: Optional[List[float]] = None

    @property
    def is_fitted(self) -> bool:
        return self.ratio is not None

    def fit_rows(self, columns: Dict[str, Sequence[float]], y: Sequence[float], excursions: Sequence[float]) -> "ExcursionModel":
        """Fit on prepared rows (see build_table / excursion_targets)."""

        self.volatility.fit_rows(columns, y)
        predicted = self.volatility.predict_log_rows(columns)
        smearing = self.volatility.smearing
        self.ratio = ratio_quantiles(excursions, [math.exp(p) * smearing for p in predicted], self.quantile_levels)

        return self

    def expected_from_log(self, log_values: Sequence[float]) -> List[float]:

        smearing = self.volatility.smearing

        return [math.exp(v) * smearing for v in log_values]

    def forecast(self, candles: Sequence) -> RiskSheet:
        """Risk sheet from the last `slow` contiguous candles (refuses across a gap)."""

        if self.ratio is None:
            raise VolatilityError("model is not fitted")

        base = self.volatility.forecast(candles)

        return RiskSheet(
            expected_range=base.expected_range,
            upper_range=base.upper_range,
            quantiles={q: base.expected_range * r for q, r in zip(self.quantile_levels, self.ratio)},
        )
