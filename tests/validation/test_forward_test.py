"""
Tests for the forward-return test.

Hand-made candles and seeded synthetic series test the MACHINERY (alignment,
gap safety, no lookahead, statistical behaviour). They say nothing about any
real market.
"""

import random

from src.analysis.smart_money import StructureType
from src.domain.models import Candle
from src.validation import (
    circular_shift_test,
    collect_samples,
    forward_returns,
    group_means,
    returns_by_year,
    signed_edge,
    structure_states,
)

UP = StructureType.BULLISH
DOWN = StructureType.BEARISH


def candle(open_, high, low, close, ts=0):
    return Candle(
        timestamp=ts, open=open_, high=high, low=low, close=close,
        volume=0, quote_volume=0, trades=0, buy_volume=0, buy_quote_volume=0,
    )


def flat_series(prices, start_ts=0, step=3_600_000):
    out = []
    for i, p in enumerate(prices):
        out.append(candle(p, p * 1.001, p * 0.999, p, start_ts + i * step))
    return out


def random_walk(n, seed, drift=0.0, phi=0.0):
    rng = random.Random(seed)
    price = 1000.0
    last = 0.0
    out = []
    for i in range(n):
        r = phi * last + rng.gauss(drift, 0.004)
        last = r
        open_ = price
        price = open_ * (1.0 + r)
        spread = open_ * rng.uniform(0.0005, 0.003)
        out.append(candle(open_, max(open_, price) + spread, min(open_, price) - spread, price, i * 3_600_000))
    return out


def test_forward_returns_alignment():
    candles = [
        candle(100, 101, 99, 100, 0),
        candle(110, 121, 109, 120, 1),
        candle(121, 133, 120, 132, 2),
        candle(130, 141, 129, 140, 3),
    ]
    out = forward_returns(candles, horizon=2)
    # i=0: entry open[1]=110, exit close[2]=132
    assert abs(out[0] - (132 / 110 - 1) * 10_000) < 1e-9
    # i=1: entry open[2]=121, exit close[3]=140
    assert abs(out[1] - (140 / 121 - 1) * 10_000) < 1e-9
    assert out[2] is None and out[3] is None


def test_forward_returns_horizon_one_uses_next_candle_only():
    candles = [candle(100, 101, 99, 100, 0), candle(110, 122, 109, 121, 1), candle(1, 2, 1, 1, 2)]
    out = forward_returns(candles, horizon=1)
    assert abs(out[0] - (121 / 110 - 1) * 10_000) < 1e-9
    assert out[1] is not None and out[2] is None


def test_invalid_horizon_is_rejected():
    for bad in (0, -1, 1.5, "2", None):
        try:
            forward_returns(flat_series([100, 101, 102]), bad)
        except ValueError:
            continue
        raise AssertionError(f"expected ValueError for {bad!r}")


def test_samples_never_cross_a_gap():
    first = flat_series([100 + i * 0.1 for i in range(120)], start_ts=0)
    second = flat_series([1000 + i * 0.1 for i in range(120)], start_ts=10**12)
    samples = collect_samples([first, second], strength=2, horizon=5)
    assert len(samples) == (120 - 5) + (120 - 5)
    assert max(abs(r) for r in samples.returns) < 500


def test_states_have_no_lookahead():
    candles = random_walk(400, seed=5)
    for strength in (2, 5):
        full = structure_states(candles, strength)
        for n in (30, 90, 211, 399):
            prefix = structure_states(candles[:n], strength)
            assert prefix[n - 1] == full[n - 1], (strength, n)


def test_states_cache_gives_identical_samples():
    segments = [random_walk(300, seed=8)]
    cache = {}
    first = collect_samples(segments, 3, 4, states_cache=cache)
    second = collect_samples(segments, 3, 4, states_cache=cache)
    assert first.states == second.states and first.returns == second.returns


def test_group_means_and_signed_edge():
    states = [UP, UP, DOWN, DOWN, StructureType.RANGING]
    returns = [10.0, 20.0, -4.0, -6.0, 999.0]
    n_up, n_down, m_up, m_down = group_means(states, returns, UP, DOWN)
    assert (n_up, n_down) == (2, 2)
    assert m_up == 15.0 and m_down == -5.0
    assert signed_edge(states, returns, UP, DOWN) == (10 + 20 + 4 + 6) / 4


def test_group_means_empty_state_is_nan():
    _, _, m_up, m_down = group_means([UP], [1.0], UP, DOWN)
    assert m_up == 1.0 and m_down != m_down


def block_states(n, rng, block=200):
    states = []
    current = UP
    for i in range(n):
        if i % block == 0:
            current = UP if rng.random() < 0.5 else DOWN
        states.append(current)
    return states


def test_shift_test_detects_a_planted_edge():
    rng = random.Random(1)
    states = block_states(6000, rng)
    returns = [rng.gauss(0, 50) + (20 if s == UP else -20) for s in states]
    observed, p = circular_shift_test(states, returns, UP, DOWN, shifts=300)
    assert observed > 30
    assert p < 0.01


def test_shift_test_does_not_invent_edges_in_noise():
    significant = 0
    for seed in range(20):
        rng = random.Random(100 + seed)
        states = block_states(6000, rng)
        returns = [rng.gauss(0, 50) for _ in states]
        _, p = circular_shift_test(states, returns, UP, DOWN, shifts=200, seed=seed)
        if p < 0.05:
            significant += 1
    assert significant <= 5


def test_shift_test_validates_inputs():
    for call in (
        lambda: circular_shift_test([UP, DOWN], [1.0], UP, DOWN),
        lambda: circular_shift_test([UP, UP, UP], [1.0, 2.0, 3.0], UP, DOWN),
        lambda: circular_shift_test(
            [UP, DOWN] * 5, [1.0] * 10, UP, DOWN, min_shift_fraction=0.9
        ),
    ):
        try:
            call()
        except ValueError:
            continue
        raise AssertionError("expected ValueError")


def test_returns_by_year_splits_and_skips_rare_years():
    year_ms = 365 * 24 * 3_600_000
    stamps, states, returns = [], [], []
    for i in range(100):
        stamps.append(1_700_000_000_000 + i * 1000)
        states.append(UP if i % 2 == 0 else DOWN)
        returns.append(5.0 if i % 2 == 0 else -5.0)
    for i in range(5):
        stamps.append(1_700_000_000_000 + year_ms + i * 1000)
        states.append(UP)
        returns.append(1.0)
    result = returns_by_year(stamps, states, returns, UP, DOWN)
    years = sorted(result)
    assert result[years[0]] == 10.0
    assert result[years[1]] is None
