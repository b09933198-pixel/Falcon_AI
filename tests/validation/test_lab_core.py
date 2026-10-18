"""
Tests for the strategy-lab indicators, statistics and trade simulator (hand-made candles).
"""

import math

from src.lab.engine import Costs, Signal, simulate, summarize
from src.lab.indicators import (
    atr_wilder, bollinger, ema, pivot_highs, pivot_lows, rsi_wilder, sma, true_ranges,
)
from src.lab.stats import betainc, binom_sf, t_sf, t_test_positive
from tests.validation.test_excursion import HOUR, mk

FREE = Costs(fee=0.0, slippage=0.0)


def flat(n, price=100.0, rng=1.0, start=0):
    """n candles, open = close = price, high/low +-rng/2."""
    return [mk((start + k) * HOUR, price, price + rng / 2, price - rng / 2, price) for k in range(n)]


def atr_of(candles, value=1.0):
    return [value] * len(candles)


# ---------------- indicators ----------------

def test_true_range_atr_and_sma_ema():
    h, l, c = [10, 12, 11], [9, 10, 8], [9.5, 11, 9]
    assert true_ranges(h, l, c) == [None, 2.5, 3]
    cs = flat(30, rng=2.0)
    atr = atr_wilder([x.high for x in cs], [x.low for x in cs], [x.close for x in cs], 14)
    assert atr[13] is None and atr[14] == 2.0 and atr[29] == 2.0
    assert sma([1, 2, 3, 4], 2) == [None, 1.5, 2.5, 3.5]
    e = ema([1, 2, 3, 4, 5], 3)
    assert e[:2] == [None, None] and e[2] == 2.0 and abs(e[3] - 3.0) < 1e-12 and abs(e[4] - 4.0) < 1e-12


def test_rsi_extremes_and_known_value():
    up = rsi_wilder([float(k) for k in range(40)], 14)
    assert up[13] is None and up[14] == 100.0 and up[39] == 100.0
    assert rsi_wilder([5.0] * 30, 14)[20] == 50.0
    down = rsi_wilder([float(40 - k) for k in range(40)], 14)
    assert down[20] == 0.0
    zig = [10.0 + (1 if k % 2 == 0 else 0) for k in range(40)]     # equal gains and losses
    assert abs(rsi_wilder(zig, 14)[30] - 50.0) < 5


def test_bollinger_population_std_and_pivots():
    closes = [1.0, 2.0, 3.0, 4.0]
    mid, up, lo, width = bollinger(closes, 4, 2.0)
    std = math.sqrt(1.25)
    assert abs(mid[3] - 2.5) < 1e-12 and abs(up[3] - (2.5 + 2 * std)) < 1e-12 and abs(width[3] - 4 * std / 2.5) < 1e-12
    assert mid[2] is None
    highs = [1, 2, 3, 9, 3, 2, 1, 2, 3, 4, 3, 2, 1]
    assert pivot_highs(highs, 3) == [3, 9]
    assert pivot_lows([5, 4, 3, 0, 3, 4, 5, 6], 3) == [3]
    assert pivot_highs([1, 5, 5, 1], 1) == []                           # strict


# ---------------- statistics ----------------

def test_binomial_and_t_distribution_against_known_values():
    assert abs(binom_sf(8, 10, 0.5) - 0.0546875) < 1e-12
    assert binom_sf(0, 10, 0.3) == 1.0 and binom_sf(11, 10, 0.3) == 0.0
    assert abs(binom_sf(130, 200, 0.58) - sum(math.comb(200, j) * 0.58 ** j * 0.42 ** (200 - j) for j in range(130, 201))) < 1e-9
    assert abs(betainc(2.0, 3.0, 0.5) - 0.6875) < 1e-12
    assert abs(t_sf(2.228138852, 10) - 0.025) < 1e-6
    assert abs(t_sf(0.0, 7) - 0.5) < 1e-12 and abs(t_sf(-2.228138852, 10) - 0.975) < 1e-6
    assert abs(t_sf(1.96, 100000) - 0.025) < 1e-4
    assert t_test_positive([1.0, 1.0, 1.0]) == 0.0 and t_test_positive([-1.0, -1.0]) == 1.0
    assert t_test_positive([1.0]) == 1.0


# ---------------- simulator, gate A ----------------

def test_gate_a_target_stop_and_tie_rule():
    cs = flat(10)
    cs[3] = mk(3 * HOUR, 100.0, 103.0, 99.5, 102.0)            # reaches +2 (target, distance 2*ATR=2)
    t, sk = simulate(cs, atr_of(cs), [Signal(2, 1)], "A", HOUR, FREE)
    assert len(t) == 1 and t[0].reason == "target" and t[0].entry == 100.0 and t[0].exit == 102.0
    assert abs(t[0].net_r - 1.0) < 1e-12 and t[0].stop_distance == 2.0

    cs = flat(10)
    cs[3] = mk(3 * HOUR, 100.0, 103.0, 97.0, 100.0)            # both inside one candle: the stop wins
    t, _ = simulate(cs, atr_of(cs), [Signal(2, 1)], "A", HOUR, FREE)
    assert t[0].reason == "stop" and abs(t[0].net_r + 1.0) < 1e-12

    cs = flat(10)
    cs[3] = mk(3 * HOUR, 100.0, 100.5, 97.5, 98.0)             # short: price down hits the short's target
    t, _ = simulate(cs, atr_of(cs), [Signal(2, -1)], "A", HOUR, FREE)
    assert t[0].reason == "target" and t[0].exit == 98.0 and abs(t[0].net_r - 1.0) < 1e-12


def test_gate_a_timeout_costs_and_funding():
    cs = flat(60)
    t, _ = simulate(cs, atr_of(cs), [Signal(2, 1)], "A", HOUR, FREE)
    assert t[0].reason == "timeout" and t[0].entry_index == 3 and t[0].exit_index == 3 + 48 - 1 and t[0].net_r == 0.0
    costs = Costs(fee=0.0006, slippage=0.0002)
    t, _ = simulate(cs, atr_of(cs), [Signal(2, 1)], "A", HOUR, costs)
    assert abs(t[0].cost_r - 0.0016 * 100.0 / 2.0) < 1e-12 and abs(t[0].net_r + 0.08) < 1e-12
    # funding: events inside (entry_open, exit_close]; a long pays a positive rate, a short receives it
    stamps = [10 * HOUR, 20 * HOUR, 200 * HOUR]
    t, _ = simulate(cs, atr_of(cs), [Signal(2, 1)], "A", HOUR, FREE, (stamps, [0.0001, 0.0002, 0.9]))
    assert abs(t[0].cost_r - 100.0 * 0.0003 / 2.0) < 1e-12
    t, _ = simulate(cs, atr_of(cs), [Signal(2, -1)], "A", HOUR, FREE, (stamps, [0.0001, 0.0002, 0.9]))
    assert abs(t[0].cost_r + 100.0 * 0.0003 / 2.0) < 1e-12


def test_no_overlap_no_next_candle_and_open_at_end():
    cs = flat(80)
    t, sk = simulate(cs, atr_of(cs), [Signal(2, 1), Signal(10, 1), Signal(60, 1)], "A", HOUR, FREE)
    assert len(t) == 1 and sk["busy"] == 1 and sk["open_at_end"] == 1           # third trade cannot finish
    cs = flat(5)
    t, sk = simulate(cs, atr_of(cs), [Signal(4, 1)], "A", HOUR, FREE)
    assert t == [] and sk["no_next_candle"] == 1
    # after an exit at candle j the next signal on candle j is allowed (entry at the open of j+1)
    cs = flat(80)
    cs[3] = mk(3 * HOUR, 100.0, 103.0, 99.5, 102.0)
    t, _ = simulate(cs, atr_of(cs), [Signal(2, 1), Signal(3, 1)], "A", HOUR, FREE)
    assert [x.entry_index for x in t][:2] == [3, 4]
    t, sk = simulate(cs, [None] * 30, [Signal(2, 1)], "A", HOUR, FREE)
    assert t == [] and sk["no_atr"] == 1


# ---------------- simulator, gate B ----------------

def test_gate_b_level_clipping_and_two_r_target():
    cs = flat(30)
    cs[4] = mk(4 * HOUR, 100.0, 106.5, 99.9, 106.0)
    # structural stop 1.5 below the entry: inside the clip range [1, 4] x ATR; target = 2R = +3
    t, _ = simulate(cs, atr_of(cs), [Signal(2, 1, stop_level=98.5)], "B", HOUR, FREE)
    assert t[0].stop_distance == 1.5 and t[0].reason == "target" and abs(t[0].net_r - 2.0) < 1e-12
    # too close (0.2) is widened to 1 x ATR; too far (9) is cut to 4 x ATR
    t, _ = simulate(cs, atr_of(cs), [Signal(2, 1, stop_level=99.8)], "B", HOUR, FREE)
    assert t[0].stop_distance == 1.0
    cs[6] = mk(6 * HOUR, 100.0, 109.0, 99.9, 108.5)
    t, _ = simulate(cs, atr_of(cs), [Signal(2, 1, stop_level=91.0)], "B", HOUR, FREE)
    assert t[0].stop_distance == 4.0 and t[0].reason == "target" and abs(t[0].net_r - 2.0) < 1e-12
    t, sk = simulate(cs, atr_of(cs), [Signal(2, 1, stop_level=101.0)], "B", HOUR, FREE)
    assert t == [] and sk["stop_wrong_side"] == 1


def test_gate_b_price_target_rule_exit_and_unclipped_atr_stop():
    cs = flat(30)
    cs[5] = mk(5 * HOUR, 100.0, 100.4, 97.0, 97.2)
    t, _ = simulate(cs, atr_of(cs), [Signal(2, -1, stop_level=101.5, target="price", target_price=97.5)], "B", HOUR, FREE)
    assert t[0].reason == "target" and t[0].exit == 97.5 and abs(t[0].net_r - 2.5 / 1.5) < 1e-12
    t, sk = simulate(cs, atr_of(cs), [Signal(2, -1, stop_level=101.5, target="price", target_price=100.5)], "B", HOUR, FREE)
    assert t == [] and sk["target_passed"] == 1
    # rule exit at the close of candle 7; stop 2 x ATR (not clipped) when no level is given
    cs = flat(30)
    t, _ = simulate(cs, atr_of(cs, 0.5), [Signal(2, 1, target="none", exit_when=lambda j: j >= 7)], "B", HOUR, FREE)
    assert t[0].reason == "rule" and t[0].exit_index == 7 and t[0].stop_distance == 1.0
    t, _ = simulate(cs, atr_of(cs), [Signal(2, 1, target="none", timeout_b=5)], "B", HOUR, FREE)
    assert t[0].reason == "timeout" and t[0].exit_index == 3 + 5 - 1
    try:
        simulate(cs, atr_of(cs), [Signal(2, 1), Signal(2, -1)], "A", HOUR, FREE)
        assert False
    except ValueError:
        pass


# ---------------- verdict ----------------

def fake_trades(wins, losses, win_r=0.8, loss_r=-1.2, cost_r=0.2):
    from src.lab.engine import Trade
    mk_t = lambda r: Trade(0, 1, 2, 1, 100.0, 100.0, 1.0, r + cost_r, cost_r, r, "x")
    return [mk_t(win_r) for _ in range(wins)] + [mk_t(loss_r) for _ in range(losses)]


def test_summarize_conditions():
    strong = summarize(fake_trades(160, 40), "A", alpha=0.003)            # 80% win rate
    assert strong["passed"] and strong["status"] == "passed" and abs(strong["breakeven"] - 0.6) < 1e-12
    weak = summarize(fake_trades(124, 76), "A", alpha=0.003)              # 62%: above 60 but not significant
    assert not weak["passed"] and weak["status"] == "failed"
    low = summarize(fake_trades(110, 90), "A", alpha=0.5)                 # 55% < 60%
    assert not low["passed"]
    few = summarize(fake_trades(80, 20), "A", alpha=0.003)
    assert few["status"] == "unproven" and not few["passed"]
    losing = summarize(fake_trades(130, 70, win_r=0.5, loss_r=-1.3), "A", alpha=0.5)   # 65% wins but mean R < 0
    assert not losing["passed"] and losing["mean_r"] < 0
    b = summarize(fake_trades(150, 50), "B", alpha=0.003)
    assert b["passed"] and b["p_t"] < 0.003
    assert summarize([], "A", 0.01)["status"] == "unproven"
