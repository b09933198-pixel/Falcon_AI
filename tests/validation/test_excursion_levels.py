"""
Tests for the per-risk-level excursion quantiles (F-007).

Hand-made numbers test the grouping and fallback rules; a seeded synthetic series
tests causality and plumbing. They say nothing about any real market.
"""

from src.analysis.volatility import build_table
from src.analysis.volatility.excursion import excursion_targets, level_ratio_quantiles
from src.analysis.volatility.forecaster import VolatilityError
from src.validation.excursion_walkforward import (
    coverage_at,
    group_rows,
    level_index,
    walk_forward_levels,
)
from tests.validation.test_excursion import HOUR, raises, synthetic


def make_training(per_level, ratios):
    """per_level rows per risk level; ratio of that level; expected range fixed at 0.01."""

    excursions, expected, ranks = [], [], []
    for level, rank in enumerate((0.1, 0.5, 0.85, 0.97)):
        for k in range(per_level[level]):
            excursions.append(0.01 * ratios[level] * (1 + 0.1 * (k % 5 - 2) / 2))
            expected.append(0.01)
            ranks.append(rank)
    return excursions, expected, ranks


def test_ratio_quantiles_are_estimated_per_level():
    e, x, r = make_training([400, 400, 400, 400], [2.0, 1.5, 1.2, 1.0])
    out = level_ratio_quantiles(e, x, r, (0.5, 0.95))
    assert len(out) == 4
    medians = [row[0] for row in out]
    assert medians[0] > medians[1] > medians[2] > medians[3]
    assert abs(medians[0] - 2.0) < 0.05 and abs(medians[3] - 1.0) < 0.05
    assert all(row[1] > row[0] for row in out)


def test_small_levels_fall_back_to_the_pooled_quantiles():
    e, x, r = make_training([400, 400, 400, 50], [2.0, 1.5, 1.2, 9.0])
    out = level_ratio_quantiles(e, x, r, (0.5,), min_rows=300)
    everything_pooled = level_ratio_quantiles(e, x, r, (0.5,), min_rows=10_000)
    assert out[3] == everything_pooled[0]         # the 50 wild rows did not set their own level
    assert abs(out[0][0] - 2.0) < 0.05


def test_rows_without_rank_are_ignored_and_input_is_validated():
    e, x, r = make_training([400, 400, 400, 400], [2.0, 1.5, 1.2, 1.0])
    with_none = r[:]
    for i in range(0, 1600, 2):
        with_none[i] = None
    out = level_ratio_quantiles(e, x, with_none, (0.5,))
    assert len(out) == 4

    assert raises(lambda: level_ratio_quantiles(e, x, r[:-1]), VolatilityError)
    assert raises(lambda: level_ratio_quantiles(e[:100], x[:100], [0.5] * 100), VolatilityError)
    assert raises(lambda: level_ratio_quantiles(e, x, [None] * len(e)), VolatilityError)


def test_walk_forward_levels_is_calibrated_and_has_no_lookahead():
    candles = synthetic(9000, seed=7)
    table = build_table([candles], horizon=24)
    e = excursion_targets([candles], horizon=24)
    kwargs = dict(horizon=24, min_train_rows=3000, refit_rows=500, rank_window=1500, min_level_rows=100)

    result = walk_forward_levels(table, e, HOUR, **kwargs)

    assert result.folds >= 5 and len(result) == len(table) - 3000
    assert len(result.ranks) == len(result)
    for q in (0.5, 0.8, 0.95):
        assert abs(coverage_at(result.excursion, result.quantiles[q]) - q) < 0.06
    assert len(group_rows([level_index(r) for r in result.ranks])) >= 3

    changed = list(e)
    for i in range(len(e) - 2500, len(e)):
        changed[i] = 9.0
    other = walk_forward_levels(table, changed, HOUR, **kwargs)

    k = 1500
    assert other.expected[:k] == result.expected[:k]
    assert other.quantiles[0.95][:k] == result.quantiles[0.95][:k]
    assert other.ranks[:k] == result.ranks[:k]


def test_walk_forward_levels_validates_input():
    candles = synthetic(3500, seed=8)
    table = build_table([candles], horizon=24)
    e = excursion_targets([candles], horizon=24)
    assert raises(lambda: walk_forward_levels(table, e[:-1], HOUR, min_train_rows=3000))
    assert raises(lambda: walk_forward_levels(table, e, HOUR, min_train_rows=100))
    assert raises(lambda: walk_forward_levels(table, e, HOUR, min_train_rows=10_000))
