"""
Falcon AI

Validation Layer

Walk-forward evaluation of the adverse-excursion quantiles (F-006)

Version: 1.0.0

Same scheme as vol_walkforward: expanding window, refit every `refit_rows`
rows, training rows whose target period reaches into the test period are
purged. The excursion ratio quantiles are measured on the (purged) training
rows only.

Baseline B: for every test row, the empirical quantile of E over the trailing
`baseline_rows` rows whose outcome was already known at the decision time.
"""

from __future__ import annotations

import math
from bisect import bisect_left, insort
from collections import deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Sequence

from src.analysis.volatility import BASE_FEATURES, VolatilityTable
from src.analysis.volatility.excursion import (
    QUANTILES,
    ExcursionModel,
    level_ratio_quantiles,
    trailing_ranks,
)
from src.analysis.volatility.forecaster import _quantile


@dataclass(frozen=True)
class ExcursionResult:
    timestamps: List[int]
    excursion: List[float]
    expected: List[float]
    quantiles: Dict[float, List[float]]
    baseline: Dict[float, List[float]]
    ranks: List[float]
    folds: int

    def __len__(self) -> int:
        return len(self.excursion)


def _slice(table: VolatilityTable, lo: int, hi: int) -> Dict[str, List[float]]:
    return {name: table.columns[name][lo:hi] for name in BASE_FEATURES}


def baseline_quantiles(
    timestamps: Sequence[int],
    excursions: Sequence[float],
    start: int,
    horizon_ms: int,
    quantiles: Sequence[float],
    window_rows: int,
    min_rows: int = 2000,
) -> Dict[float, List[float]]:
    """Trailing unconditional quantiles for rows start..end, using only known outcomes."""

    ordered: List[float] = []
    queue: deque = deque()
    nxt = 0
    out: Dict[float, List[float]] = {q: [] for q in quantiles}

    for i in range(start, len(excursions)):

        # a row's outcome is known once its holding period is over
        while nxt < i and timestamps[nxt] + horizon_ms <= timestamps[i]:
            insort(ordered, excursions[nxt])
            queue.append(excursions[nxt])
            nxt += 1

            if len(queue) > window_rows:
                old = queue.popleft()
                del ordered[bisect_left(ordered, old)]

        if len(ordered) < min_rows:
            raise ValueError("not enough known outcomes for the baseline")

        for q in quantiles:
            out[q].append(_quantile(ordered, q))

    return out


def walk_forward_excursion(
    table: VolatilityTable,
    excursions: Sequence[float],
    interval_ms: int,
    horizon: int = 24,
    min_train_rows: int = 17_520,
    refit_rows: int = 2_160,
    rank_window: int = 8_760,
    quantiles: Sequence[float] = QUANTILES,
) -> ExcursionResult:
    """Out-of-sample quantile forecasts for every row from `min_train_rows` on."""

    n = len(table)

    if len(excursions) != n:
        raise ValueError("excursions must align with the table rows")

    if min_train_rows < 2000 or refit_rows < 1:
        raise ValueError("min_train_rows must be >= 2000 and refit_rows >= 1")

    if n <= min_train_rows:
        raise ValueError("not enough rows for a walk-forward test")

    stamps = table.timestamps
    horizon_ms = horizon * interval_ms

    out_ts: List[int] = []
    out_e: List[float] = []
    out_expected: List[float] = []
    out_q: Dict[float, List[float]] = {q: [] for q in quantiles}
    log_all: List[float] = []                 # predicted log range for EVERY row (rank history)
    folds = 0

    start = min_train_rows

    while start < n:

        stop = min(start + refit_rows, n)
        cutoff = bisect_left(stamps, stamps[start] - horizon_ms)

        model = ExcursionModel(interval_ms, horizon, quantiles)
        model.fit_rows(_slice(table, 0, cutoff), table.y[:cutoff], list(excursions[:cutoff]))

        if folds == 0:
            log_all.extend(model.volatility.predict_log_rows(_slice(table, 0, start)))

        predicted = model.volatility.predict_log_rows(_slice(table, start, stop))
        expected = model.expected_from_log(predicted)

        log_all.extend(predicted)
        out_ts.extend(stamps[start:stop])
        out_e.extend(excursions[start:stop])
        out_expected.extend(expected)

        for q, ratio in zip(quantiles, model.ratio):
            out_q[q].extend(x * ratio for x in expected)

        folds += 1
        start = stop

    ranks_all = trailing_ranks(log_all, rank_window, min_valid=min(2000, rank_window))
    ranks = ranks_all[min_train_rows:]

    if any(r is None for r in ranks):
        raise ValueError("risk-level history too short")

    baseline = baseline_quantiles(
        stamps, excursions, min_train_rows, horizon_ms, quantiles, rank_window, min_rows=min(2000, rank_window)
    )

    return ExcursionResult(out_ts, out_e, out_expected, out_q, baseline, ranks, folds)


def walk_forward_levels(
    table: VolatilityTable,
    excursions: Sequence[float],
    interval_ms: int,
    horizon: int = 24,
    min_train_rows: int = 17_520,
    refit_rows: int = 2_160,
    rank_window: int = 8_760,
    quantiles: Sequence[float] = QUANTILES,
    min_level_rows: int = 300,
) -> ExcursionResult:
    """F-007: like walk_forward_excursion, but the ratio quantiles are estimated per risk level.

    At every refit the model predicts ln(expected range) for all rows up to the end of the fold;
    the trailing rank of that series defines each row's risk level. Training rows (purged) fit the
    per-level ratio quantiles; test rows use the level of their own (causal) rank.
    """

    n = len(table)

    if len(excursions) != n:
        raise ValueError("excursions must align with the table rows")

    if min_train_rows < 2000 or refit_rows < 1:
        raise ValueError("min_train_rows must be >= 2000 and refit_rows >= 1")

    if n <= min_train_rows:
        raise ValueError("not enough rows for a walk-forward test")

    stamps = table.timestamps
    horizon_ms = horizon * interval_ms
    min_valid = min(2000, rank_window)

    out_ts: List[int] = []
    out_e: List[float] = []
    out_expected: List[float] = []
    out_q: Dict[float, List[float]] = {q: [] for q in quantiles}
    out_ranks: List[float] = []
    folds = 0

    start = min_train_rows

    while start < n:

        stop = min(start + refit_rows, n)
        cutoff = bisect_left(stamps, stamps[start] - horizon_ms)

        model = ExcursionModel(interval_ms, horizon, quantiles)
        model.fit_rows(_slice(table, 0, cutoff), table.y[:cutoff], list(excursions[:cutoff]))

        predicted_all = model.volatility.predict_log_rows(_slice(table, 0, stop))
        expected_all = model.expected_from_log(predicted_all)
        ranks_all = trailing_ranks(predicted_all, rank_window, min_valid)

        test_ranks = ranks_all[start:stop]

        if any(r is None for r in test_ranks):
            raise ValueError("risk-level history too short")

        ratios = level_ratio_quantiles(
            excursions[:cutoff], expected_all[:cutoff], ranks_all[:cutoff], quantiles, min_level_rows
        )

        out_ts.extend(stamps[start:stop])
        out_e.extend(excursions[start:stop])
        out_expected.extend(expected_all[start:stop])
        out_ranks.extend(test_ranks)

        for j, q in enumerate(quantiles):
            out_q[q].extend(
                x * ratios[level_index(r)][j] for x, r in zip(expected_all[start:stop], test_ranks)
            )

        folds += 1
        start = stop

    baseline = baseline_quantiles(
        stamps, excursions, min_train_rows, horizon_ms, quantiles, rank_window, min_rows=min_valid
    )

    return ExcursionResult(out_ts, out_e, out_expected, out_q, baseline, out_ranks, folds)


# ----------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------

def coverage_at(values: Sequence[float], bounds: Sequence[float]) -> float:
    """Fraction of rows where the realised value stayed at or below its bound."""

    if len(values) != len(bounds) or not values:
        raise ValueError("series must be non-empty and of equal length")

    return sum(1 for v, b in zip(values, bounds) if v <= b) / len(values)


def pinball_loss(values: Sequence[float], bounds: Sequence[float], q: float) -> float:
    """Mean quantile (pinball) loss; lower is better."""

    if len(values) != len(bounds) or not values:
        raise ValueError("series must be non-empty and of equal length")

    total = 0.0

    for v, b in zip(values, bounds):
        d = v - b
        total += q * d if d >= 0 else (q - 1.0) * d

    return total / len(values)


def level_index(rank: float, bounds: Sequence[float] = (0.25, 0.75, 0.95)) -> int:
    """0 = low .. 3 = extreme."""

    for k, b in enumerate(bounds):
        if rank < b:
            return k

    return len(bounds)


def group_rows(keys: Sequence[int]) -> Dict[int, List[int]]:

    groups: Dict[int, List[int]] = {}

    for i, k in enumerate(keys):
        groups.setdefault(k, []).append(i)

    return groups


def median(values: Sequence[float]) -> float:

    if not values:
        raise ValueError("no values")

    return _quantile(sorted(values), 0.5)


def utc_year(timestamp_ms: int) -> int:
    return datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc).year
