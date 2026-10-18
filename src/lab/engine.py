"""
Falcon AI

Strategy Lab

Trade simulator (docs/STRATEGIES_F009.md, common definitions and gates)

Version: 1.0.0

Interpretations of points the rule document leaves open (they are printed with every result):
  - "timeout N candles" = the trade is held at most N candles, entry candle included; at the close of the N-th
    candle the trade is closed at the close price.
  - Funding events with entry_open < calc_time <= close time of the exit candle are charged.
  - A signal whose structural stop is on the wrong side of the entry (gap), or whose measured-move target is
    already behind the entry, is skipped and counted. A trade still open when the data ends is discarded and counted.
  - win = net R after costs > 0. The cost-adjusted break-even win rate of gate A is (1 + mean cost in R) / 2.
"""

from __future__ import annotations

from bisect import bisect_right
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from src.lab.stats import binom_sf, t_test_positive

GATE_A_TIMEOUT = 48
CLIP_LOW, CLIP_HIGH = 1.0, 4.0
GATE_B_RR = 2.0


@dataclass(frozen=True)
class Signal:
    index: int
    direction: int
    stop_level: Optional[float] = None          # gate B structural stop; None = 2 x ATR, not clipped
    target: str = "rr"                          # gate B target: "rr" (2R) | "price" | "none"
    target_price: Optional[float] = None
    exit_when: Optional[Callable[[int], bool]] = None   # gate B rule exit, evaluated at the close of candle j
    timeout_b: int = 96


@dataclass(frozen=True)
class Costs:
    fee: float = 0.0006
    slippage: float = 0.0002
    scale: float = 1.0

    def round_trip(self) -> float:
        return 2.0 * (self.fee + self.slippage) * self.scale


@dataclass(frozen=True)
class Trade:
    signal_index: int
    entry_index: int
    exit_index: int
    direction: int
    entry: float
    exit: float
    stop_distance: float
    gross_r: float
    cost_r: float
    net_r: float
    reason: str


def _funding_sum(funding, start_ms: int, end_ms: int) -> float:
    if not funding:
        return 0.0
    stamps, rates = funding
    lo = bisect_right(stamps, start_ms)
    hi = bisect_right(stamps, end_ms)
    return sum(rates[lo:hi])


def simulate(
    candles: Sequence,
    atr: Sequence[Optional[float]],
    signals: Sequence[Signal],
    gate: str,
    interval_ms: int,
    costs: Costs = Costs(),
    funding: Optional[Tuple[Sequence[int], Sequence[float]]] = None,
) -> Tuple[List[Trade], Dict[str, int]]:
    """Run the signals through the candles. Returns (trades, counters of skipped situations)."""

    if gate not in ("A", "B"):
        raise ValueError("gate must be 'A' or 'B'")

    n = len(candles)

    if len({s.index for s in signals}) != len(signals):
        raise ValueError("two signals on the same candle: the rule must drop them")

    skipped = {"busy": 0, "no_atr": 0, "no_next_candle": 0, "stop_wrong_side": 0, "target_passed": 0, "open_at_end": 0}
    trades: List[Trade] = []
    next_free = 0

    for s in sorted(signals, key=lambda x: x.index):

        if s.index < next_free:
            skipped["busy"] += 1
            continue

        e = s.index + 1

        if e >= n:
            skipped["no_next_candle"] += 1
            continue

        a = atr[s.index]

        if a is None or a <= 0:
            skipped["no_atr"] += 1
            continue

        d = s.direction
        entry = candles[e].open
        exit_rule = None
        target_price: Optional[float]

        if gate == "A":
            dist = 2.0 * a
            timeout = GATE_A_TIMEOUT
            target_price = entry + d * dist
        else:
            timeout = s.timeout_b
            exit_rule = s.exit_when

            if s.stop_level is None:
                dist = 2.0 * a
            else:
                raw = (entry - s.stop_level) * d

                if raw <= 0:
                    skipped["stop_wrong_side"] += 1
                    continue

                dist = min(max(raw, CLIP_LOW * a), CLIP_HIGH * a)

            if s.target == "rr":
                target_price = entry + d * GATE_B_RR * dist
            elif s.target == "price":
                target_price = s.target_price

                if target_price is None or (target_price - entry) * d <= 0:
                    skipped["target_passed"] += 1
                    continue
            else:
                target_price = None

        stop_price = entry - d * dist
        exit_index = None
        exit_price = 0.0
        reason = ""

        for j in range(e, e + timeout):

            if j >= n:
                break

            c = candles[j]
            hit_stop = c.low <= stop_price if d == 1 else c.high >= stop_price
            hit_target = target_price is not None and (c.high >= target_price if d == 1 else c.low <= target_price)

            if hit_stop:
                exit_index, exit_price, reason = j, stop_price, "stop"
            elif hit_target:
                exit_index, exit_price, reason = j, target_price, "target"
            elif exit_rule is not None and exit_rule(j):
                exit_index, exit_price, reason = j, c.close, "rule"
            elif j == e + timeout - 1:
                exit_index, exit_price, reason = j, c.close, "timeout"

            if exit_index is not None:
                break

        if exit_index is None:
            skipped["open_at_end"] += 1
            break

        gross = d * (exit_price - entry)
        cost = costs.round_trip() * entry
        cost += d * entry * _funding_sum(funding, candles[e].timestamp, candles[exit_index].timestamp + interval_ms)

        trades.append(Trade(
            signal_index=s.index, entry_index=e, exit_index=exit_index, direction=d, entry=entry, exit=exit_price,
            stop_distance=dist, gross_r=gross / dist, cost_r=cost / dist, net_r=(gross - cost) / dist, reason=reason,
        ))
        next_free = exit_index

    return trades, skipped


def summarize(trades: Sequence[Trade], gate: str, alpha: float, min_trades: int = 200, min_win: float = 0.60) -> Dict:
    """Numbers and the pass/fail verdict of one strategy x gate (F-009 pass conditions)."""

    n = len(trades)
    out: Dict = {"gate": gate, "trades": n, "alpha": alpha}

    if n == 0:
        out.update(wins=0, win_rate=None, mean_r=None, breakeven=None, p_binom=None, p_t=None, status="unproven", passed=False)
        return out

    rs = [t.net_r for t in trades]
    wins = sum(1 for r in rs if r > 0)
    mean_r = sum(rs) / n
    breakeven = min(1.0, (1.0 + sum(t.cost_r for t in trades) / n) / 2.0)
    p_binom = binom_sf(wins, n, breakeven)
    p_t = t_test_positive(rs)
    p_gate = p_binom if gate == "A" else p_t
    enough = n >= min_trades
    passed = enough and wins / n >= min_win and mean_r > 0 and p_gate < alpha

    out.update(
        wins=wins, win_rate=wins / n, mean_r=mean_r, breakeven=breakeven, p_binom=p_binom, p_t=p_t,
        status="passed" if passed else ("unproven" if not enough else "failed"), passed=passed,
    )

    return out
