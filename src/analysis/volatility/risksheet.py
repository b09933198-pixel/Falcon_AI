"""
Falcon AI

Analysis Layer

Risk sheet model (F-007 version): volatility forecast + per-risk-level excursion quantiles

Version: 1.0.0

`fit_sheet_model` fits on contiguous candle segments and returns a plain, serialisable
`SheetModel`. `make_sheets` turns the newest candles into sheets: expected range, risk
level (trailing rank of the predicted ln range) and the q50 / q80 / q95 excursion
quantiles. Nothing here forecasts direction.

The pre-registered evidence is research/FINDINGS.md (F-006, F-007) and the live test F-008.
"""

from __future__ import annotations

import json
import math
from dataclasses import asdict, dataclass
from typing import Dict, List, Optional, Sequence, Tuple

from src.analysis.volatility.excursion import (
    QUANTILES,
    ExcursionModel,
    excursion_targets,
    level_ratio_quantiles,
    risk_level,
    trailing_ranks,
)
from src.analysis.volatility.forecaster import _FLOOR, VolatilityError, build_table, time_features
from src.validation.volatility_test import log_ranges, past_mean


@dataclass(frozen=True)
class SheetModel:
    interval_ms: int
    horizon: int
    fast: int
    slow: int
    rank_window: int
    coefficients: List[float]
    smearing: float
    quantiles: List[float]
    ratios: List[List[float]]          # [risk level][quantile]
    train_rows: int
    cutoff_ms: int                      # open time of the last training row
    fit_ms: int                         # wall-clock time of the fit (informational)

    def to_json(self) -> str:
        return json.dumps(asdict(self), sort_keys=True)

    @staticmethod
    def from_json(text: str) -> "SheetModel":
        raw = json.loads(text)
        return SheetModel(**raw)


@dataclass(frozen=True)
class Sheet:
    decision_open_ms: int               # open time of the candle whose close is the decision time
    expected_range: float
    quantiles: Dict[float, float]       # fractions of price
    rank: float
    level: str
    log_expected: float


def fit_sheet_model(
    segments: Sequence[Sequence],
    interval_ms: int,
    fit_ms: int,
    horizon: int = 24,
    rank_window: int = 8_760,
    min_level_rows: int = 300,
    fast: int = 24,
    slow: int = 168,
) -> SheetModel:
    """Fit on all rows that have a complete past and a complete future."""

    table = build_table(segments, horizon, fast, slow)
    excursions = excursion_targets(segments, horizon, fast, slow)

    model = ExcursionModel(interval_ms, horizon).fit_rows(table.columns, table.y, excursions)

    predicted = model.volatility.predict_log_rows(table.columns)
    expected = model.expected_from_log(predicted)
    ranks = trailing_ranks(predicted, rank_window, min(2000, rank_window))
    ratios = level_ratio_quantiles(excursions, expected, ranks, QUANTILES, min_level_rows)

    return SheetModel(
        interval_ms=interval_ms,
        horizon=horizon,
        fast=fast,
        slow=slow,
        rank_window=rank_window,
        coefficients=list(model.volatility.coefficients),
        smearing=model.volatility.smearing,
        quantiles=list(QUANTILES),
        ratios=[list(row) for row in ratios],
        train_rows=len(table),
        cutoff_ms=table.timestamps[-1],
        fit_ms=fit_ms,
    )


def feature_predictions(model: SheetModel, segments: Sequence[Sequence]) -> List[Tuple[int, float]]:
    """(open_time, predicted ln expected range) for every candle that has a complete past.

    No future is needed, so the newest candles are included. Same formula as
    VolatilityForecaster.forecast.
    """

    c = model.coefficients
    out: List[Tuple[int, float]] = []

    for segment in segments:

        ranges = log_ranges(segment)
        fast_mean = past_mean(ranges, model.fast)
        slow_mean = past_mean(ranges, model.slow)

        for i, candle in enumerate(segment):

            if fast_mean[i] is None or slow_mean[i] is None:
                continue

            s1, c1, s2, c2 = time_features(candle.timestamp)
            features = (
                math.log(max(fast_mean[i], _FLOOR)),
                math.log(max(slow_mean[i], _FLOOR)),
                s1, c1, s2, c2,
            )

            out.append((candle.timestamp, c[0] + sum(w * f for w, f in zip(c[1:], features))))

    return out


def make_sheets(
    model: SheetModel,
    segments: Sequence[Sequence],
    decision_opens: Sequence[int],
) -> Dict[int, Sheet]:
    """Sheets for the requested candles (by open time). Candles without enough history are skipped."""

    predictions = feature_predictions(model, segments)

    if not predictions:
        return {}

    stamps = [p[0] for p in predictions]
    logs = [p[1] for p in predictions]
    ranks = trailing_ranks(logs, model.rank_window, min(2000, model.rank_window))
    position = {t: k for k, t in enumerate(stamps)}

    out: Dict[int, Sheet] = {}

    for t in decision_opens:

        k = position.get(t)

        if k is None or ranks[k] is None:
            continue

        level = risk_level(ranks[k])
        expected = math.exp(logs[k]) * model.smearing
        row = model.ratios[("low", "normal", "high", "extreme").index(level)]

        out[t] = Sheet(
            decision_open_ms=t,
            expected_range=expected,
            quantiles={q: expected * r for q, r in zip(model.quantiles, row)},
            rank=ranks[k],
            level=level,
            log_expected=logs[k],
        )

    return out


def split_contiguous(candles: Sequence, interval_ms: int) -> List[List]:
    """Cut a time-ordered candle list into gap-free segments."""

    segments: List[List] = []
    current: List = []

    for candle in candles:

        if current:
            delta = candle.timestamp - current[-1].timestamp

            if delta <= 0:
                raise VolatilityError("candles must be strictly increasing in time")

            if delta != interval_ms:
                segments.append(current)
                current = []

        current.append(candle)

    if current:
        segments.append(current)

    return segments
