"""
Falcon AI

Validation Layer

Walk-forward evaluation of the volatility forecaster

Version: 1.0.0

The forecaster is refitted on an expanding window every `refit_rows` rows and
scored only on rows AFTER the window. Training rows whose target period
reaches into the test period are purged, so no outcome leaks into the model.

Reference forecasts ("naive") get the same treatment: each is shifted by the
mean training error, so they are not handicapped by a constant bias.
"""

from __future__ import annotations

import math
from bisect import bisect_left
from dataclasses import dataclass
from datetime import datetime, timezone
from operator import mul
from typing import Dict, List, Sequence, Tuple

from src.analysis.volatility import BASE_FEATURES, VolatilityForecaster, VolatilityTable


@dataclass(frozen=True)
class WalkForwardResult:
    timestamps: List[int]
    y: List[float]
    pred: List[float]
    upper: List[float]
    naive: Dict[str, List[float]]
    folds: int

    def __len__(self) -> int:
        return len(self.y)


def _slice(table: VolatilityTable, lo: int, hi: int) -> Dict[str, List[float]]:
    return {name: table.columns[name][lo:hi] for name in BASE_FEATURES}


def walk_forward(
    table: VolatilityTable,
    interval_ms: int,
    horizon: int = 24,
    min_train_rows: int = 17_520,
    refit_rows: int = 2_160,
    upper_quantile: float = 0.90,
) -> WalkForwardResult:
    """Out-of-sample forecasts for every row from `min_train_rows` on."""

    n = len(table)

    if min_train_rows < 200 or refit_rows < 1:
        raise ValueError("min_train_rows must be >= 200 and refit_rows >= 1")

    if n <= min_train_rows:
        raise ValueError("not enough rows for a walk-forward test")

    stamps = table.timestamps
    out_ts: List[int] = []
    out_y: List[float] = []
    out_pred: List[float] = []
    out_upper: List[float] = []
    out_naive: Dict[str, List[float]] = {name: [] for name in table.naive}
    folds = 0

    start = min_train_rows

    while start < n:

        stop = min(start + refit_rows, n)

        # rows whose whole target period ended before the test start
        cutoff = bisect_left(stamps, stamps[start] - horizon * interval_ms)

        if cutoff < 200:
            raise ValueError("training window too small after purging")

        model = VolatilityForecaster(
            interval_ms=interval_ms, horizon=horizon, upper_quantile=upper_quantile
        )
        model.fit_rows(_slice(table, 0, cutoff), table.y[:cutoff])

        test_columns = _slice(table, start, stop)
        predicted = model.predict_log_rows(test_columns)

        out_ts.extend(stamps[start:stop])
        out_y.extend(table.y[start:stop])
        out_pred.extend(predicted)
        out_upper.extend(p + model.upper_shift for p in predicted)

        for name, series in table.naive.items():

            bias = sum(a - b for a, b in zip(table.y[:cutoff], series[:cutoff])) / cutoff
            out_naive[name].extend(v + bias for v in series[start:stop])

        folds += 1
        start = stop

    return WalkForwardResult(out_ts, out_y, out_pred, out_upper, out_naive, folds)


# ----------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------

def mse(y: Sequence[float], predicted: Sequence[float]) -> float:

    if len(y) != len(predicted) or not y:
        raise ValueError("series must be non-empty and of equal length")

    return sum((a - b) ** 2 for a, b in zip(y, predicted)) / len(y)


def calibration_slope(predicted: Sequence[float], y: Sequence[float]) -> float:
    """Slope of y on predicted (1.0 = perfectly calibrated spread)."""

    n = len(y)

    if n != len(predicted) or n < 3:
        raise ValueError("need at least 3 paired values")

    mp = sum(predicted) / n
    my = sum(y) / n
    var = sum((p - mp) ** 2 for p in predicted)

    if var == 0:
        raise ValueError("predictions are constant")

    return sum((p - mp) * (v - my) for p, v in zip(predicted, y)) / var


def decile_table(
    predicted: Sequence[float],
    y: Sequence[float],
    groups: int = 10,
) -> List[Tuple[float, float]]:
    """[(mean predicted range, mean realised range)] from lowest to highest prediction.

    Ranges are on the original scale (exp of the log values).
    """

    n = len(y)

    if n != len(predicted) or n < groups:
        raise ValueError("not enough rows for the requested groups")

    order = sorted(range(n), key=lambda i: predicted[i])
    table: List[Tuple[float, float]] = []

    for g in range(groups):

        lo = g * n // groups
        hi = (g + 1) * n // groups
        picked = order[lo:hi]

        table.append((
            sum(math.exp(predicted[i]) for i in picked) / len(picked),
            sum(math.exp(y[i]) for i in picked) / len(picked),
        ))

    return table


def rising_steps(values: Sequence[float]) -> int:
    """How many consecutive steps go up."""

    return sum(1 for a, b in zip(values, values[1:]) if b > a)


def coverage(y: Sequence[float], upper: Sequence[float]) -> float:
    """Fraction of rows where the realised value stayed at or below the bound."""

    if len(y) != len(upper) or not y:
        raise ValueError("series must be non-empty and of equal length")

    return sum(1 for a, b in zip(y, upper) if a <= b) / len(y)


def yearly_comparison(
    timestamps: Sequence[int],
    y: Sequence[float],
    model: Sequence[float],
    references: Sequence[Sequence[float]],
    min_rows: int = 2000,
) -> Dict[int, Tuple[float, float]]:
    """Per UTC year with enough rows: (model MSE, best reference MSE)."""

    buckets: Dict[int, List[int]] = {}

    for i, stamp in enumerate(timestamps):
        year = datetime.fromtimestamp(stamp / 1000, tz=timezone.utc).year
        buckets.setdefault(year, []).append(i)

    result: Dict[int, Tuple[float, float]] = {}

    for year, index in sorted(buckets.items()):

        if len(index) < min_rows:
            continue

        ys = [y[i] for i in index]
        model_error = mse(ys, [model[i] for i in index])
        best = min(mse(ys, [ref[i] for i in index]) for ref in references)
        result[year] = (model_error, best)

    return result
