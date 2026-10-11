"""
Falcon AI

Analysis Layer

Volatility forecaster

Version: 1.0.0

Forecasts the average candle range (ln(high / low)) of the next `horizon`
candles from information known at the close of the current candle:

  - ln(mean candle range over the last `fast` candles)
  - ln(mean candle range over the last `slow` candles)
  - time of day (sin/cos of the 24h cycle, two harmonics)

The model is a plain least-squares fit in log space (see F-002 / V-1 in
research/FINDINGS.md: out-of-sample R2 about 0.40 on BTCUSDT and ETHUSDT).

What it returns
---------------
  expected_range  typical average candle range over the next horizon
                  (bias-corrected back from log space, Duan smearing)
  upper_range     an upper bound that the realised average range stays
                  under about `upper_quantile` of the time (default 90 %)

It does NOT forecast direction. Use it for stop distance, position size and
"is the market too quiet / too wild" filters, and only after
tools/check_vol_forecast.py has passed on the data in use.

Gaps: a forecast is refused when the candles it needs are not contiguous.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from src.validation.volatility_test import (
    log_ranges,
    ols_fit,
    ols_predict,
    past_mean,
    future_mean,
)

BASE_FEATURES = ("vol_fast", "vol_slow", "sin1", "cos1", "sin2", "cos2")

_FLOOR = 1e-6
_DAY_MS = 86_400_000


class VolatilityError(ValueError):
    """The forecaster cannot produce a trustworthy number."""


@dataclass(frozen=True)
class VolatilityForecast:
    expected_range: float
    upper_range: float
    log_expected: float


@dataclass(frozen=True)
class VolatilityTable:
    """Aligned rows in time order. `naive` holds reference forecasts (log space)."""

    y: List[float]
    columns: Dict[str, List[float]]
    naive: Dict[str, List[float]]
    timestamps: List[int]

    def __len__(self) -> int:
        return len(self.y)


def ewma(values: Sequence[float], halflife: float) -> List[float]:
    """Exponentially weighted mean; seeded with the first value."""

    if halflife <= 0:
        raise ValueError("halflife must be > 0")

    alpha = 1.0 - 0.5 ** (1.0 / halflife)
    out: List[float] = []
    state: Optional[float] = None

    for v in values:
        state = v if state is None else state + alpha * (v - state)
        out.append(state)

    return out


def time_features(timestamp: int) -> Tuple[float, float, float, float]:

    angle = 2.0 * math.pi * (timestamp % _DAY_MS) / _DAY_MS

    return (
        math.sin(angle), math.cos(angle),
        math.sin(2.0 * angle), math.cos(2.0 * angle),
    )


def build_table(
    segments: Sequence[Sequence],
    horizon: int = 24,
    fast: int = 24,
    slow: int = 168,
    ewma_halflife: float = 24.0,
) -> VolatilityTable:
    """Training/evaluation rows. A row exists only when every window is complete
    inside its segment, so no window crosses a data gap."""

    y: List[float] = []
    columns: Dict[str, List[float]] = {name: [] for name in BASE_FEATURES}
    naive: Dict[str, List[float]] = {"persistence": [], "ewma": []}
    timestamps: List[int] = []

    for segment in segments:

        ranges = log_ranges(segment)
        fast_mean = past_mean(ranges, fast)
        slow_mean = past_mean(ranges, slow)
        ahead = future_mean(ranges, horizon)
        smooth = ewma(ranges, ewma_halflife)

        for i, candle in enumerate(segment):

            if fast_mean[i] is None or slow_mean[i] is None or ahead[i] is None:
                continue

            s1, c1, s2, c2 = time_features(candle.timestamp)

            y.append(math.log(max(ahead[i], _FLOOR)))
            columns["vol_fast"].append(math.log(max(fast_mean[i], _FLOOR)))
            columns["vol_slow"].append(math.log(max(slow_mean[i], _FLOOR)))
            columns["sin1"].append(s1)
            columns["cos1"].append(c1)
            columns["sin2"].append(s2)
            columns["cos2"].append(c2)
            naive["persistence"].append(math.log(max(fast_mean[i], _FLOOR)))
            naive["ewma"].append(math.log(max(smooth[i], _FLOOR)))
            timestamps.append(candle.timestamp)

    return VolatilityTable(y, columns, naive, timestamps)


def _quantile(sorted_values: Sequence[float], q: float) -> float:

    if not sorted_values:
        raise ValueError("no values")

    position = q * (len(sorted_values) - 1)
    low = int(math.floor(position))
    high = int(math.ceil(position))

    if low == high:
        return sorted_values[low]

    weight = position - low

    return sorted_values[low] * (1.0 - weight) + sorted_values[high] * weight


class VolatilityForecaster:
    """Least-squares volatility forecaster (log space)."""

    def __init__(
        self,
        interval_ms: int,
        horizon: int = 24,
        fast: int = 24,
        slow: int = 168,
        upper_quantile: float = 0.90,
    ):

        if not isinstance(interval_ms, int) or interval_ms <= 0:
            raise ValueError("interval_ms must be a positive integer")

        if not 0.5 < upper_quantile < 1.0:
            raise ValueError("upper_quantile must be in (0.5, 1)")

        if fast < 1 or slow < fast or horizon < 1:
            raise ValueError("need 1 <= fast <= slow and horizon >= 1")

        self.interval_ms = interval_ms
        self.horizon = horizon
        self.fast = fast
        self.slow = slow
        self.upper_quantile = upper_quantile

        self.coefficients: Optional[List[float]] = None
        self.smearing: float = 1.0
        self.upper_shift: float = 0.0
        self.train_rows: int = 0

    # ------------------------------------------------------------------
    # Fitting
    # ------------------------------------------------------------------

    @property
    def is_fitted(self) -> bool:
        return self.coefficients is not None

    def fit_rows(self, columns: Dict[str, Sequence[float]], y: Sequence[float]) -> "VolatilityForecaster":
        """Fit on prepared rows (see build_table)."""

        design = [columns[name] for name in BASE_FEATURES]

        if len(y) < 200:
            raise VolatilityError("need at least 200 training rows")

        coefficients = ols_fit(design, y)
        fitted = ols_predict(coefficients, design)
        residual = sorted(v - p for v, p in zip(y, fitted))

        self.coefficients = coefficients
        self.smearing = sum(math.exp(r) for r in residual) / len(residual)
        self.upper_shift = _quantile(residual, self.upper_quantile)
        self.train_rows = len(y)

        return self

    def fit(self, segments: Sequence[Sequence]) -> "VolatilityForecaster":
        """Fit on contiguous candle segments (data gaps are never crossed)."""

        table = build_table(segments, self.horizon, self.fast, self.slow)

        return self.fit_rows(table.columns, table.y)

    # ------------------------------------------------------------------
    # Forecasting
    # ------------------------------------------------------------------

    def predict_log_rows(self, columns: Dict[str, Sequence[float]]) -> List[float]:
        """ln(expected average range) for prepared rows."""

        if self.coefficients is None:
            raise VolatilityError("forecaster is not fitted")

        return ols_predict(self.coefficients, [columns[name] for name in BASE_FEATURES])

    def forecast(self, candles: Sequence) -> VolatilityForecast:
        """Forecast for the next `horizon` candles, from the last `slow` candles."""

        if self.coefficients is None:
            raise VolatilityError("forecaster is not fitted")

        if len(candles) < self.slow:
            raise VolatilityError(f"need at least {self.slow} candles")

        window = candles[-self.slow:]

        for previous, current in zip(window, window[1:]):
            if current.timestamp - previous.timestamp != self.interval_ms:
                raise VolatilityError("candles are not contiguous; refusing to forecast across a gap")

        ranges = log_ranges(window)
        fast_value = sum(ranges[-self.fast:]) / self.fast
        slow_value = sum(ranges) / self.slow

        s1, c1, s2, c2 = time_features(window[-1].timestamp)

        features = [
            math.log(max(fast_value, _FLOOR)),
            math.log(max(slow_value, _FLOOR)),
            s1, c1, s2, c2,
        ]

        log_value = self.coefficients[0] + sum(
            c * f for c, f in zip(self.coefficients[1:], features)
        )

        return VolatilityForecast(
            expected_range=math.exp(log_value) * self.smearing,
            upper_range=math.exp(log_value + self.upper_shift),
            log_expected=log_value,
        )
