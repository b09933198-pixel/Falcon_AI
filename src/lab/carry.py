"""
Falcon AI

Lab

Funding-rate carry (F-013): long spot / short perpetual of equal size, funding income only

Version: 1.0.0

Rule R (pre-registered in research/FINDINGS.md, F-013). Rates are fractions per funding event
(0.0001 = 0.01%). Positive rate: longs pay shorts, so the short leg of the carry receives it.
Nothing here models the spot / perpetual price difference, liquidation or transfer costs.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Sequence

DAY_MS = 86_400_000
YEAR_DAYS = 365.0


@dataclass(frozen=True)
class CarryParams:
    entry_window_days: float
    entry_daily_rate: float
    exit_window_days: float
    exit_daily_rate: float
    max_hold_days: float
    round_trip_cost: float          # fraction of the position size N
    capital_factor: float           # capital = capital_factor x N


@dataclass(frozen=True)
class CarryTrade:
    symbol: str
    entry_ms: int
    exit_ms: int
    funding: float                  # sum of the collected rates, fraction of N
    reason: str                     # "rate", "max_hold" or "end"


def trailing_daily(times: Sequence[int], rates: Sequence[float], window_days: float) -> List[float]:
    """Sum of the rates of the events in (t - window, t] divided by the window in days, for each event t."""

    window = int(window_days * DAY_MS)
    out: List[float] = []
    start = 0

    for k in range(len(times)):
        while times[start] <= times[k] - window:
            start += 1
        out.append(sum(rates[start:k + 1]) / window_days)

    return out


def simulate_carry(symbol: str, times: Sequence[int], rates: Sequence[float], params: CarryParams) -> List[CarryTrade]:
    """Enter after an event with a high 7-day average, collect every later event, leave after an event
    with a low 3-day average, after max_hold_days, or at the end of the data."""

    if len(times) != len(rates):
        raise ValueError("times and rates differ in length")

    if any(b <= a for a, b in zip(times, times[1:])):
        raise ValueError("event times must be strictly increasing")

    n = len(times)
    d_in = trailing_daily(times, rates, params.entry_window_days)
    d_out = trailing_daily(times, rates, params.exit_window_days)
    warmup = int(params.entry_window_days * DAY_MS)
    max_hold = int(params.max_hold_days * DAY_MS)

    trades: List[CarryTrade] = []
    k = 0

    while k < n - 1:

        if times[k] - times[0] >= warmup and d_in[k] >= params.entry_daily_rate:

            funding = 0.0
            reason = "end"
            j = k

            while j < n - 1:
                j += 1
                funding += rates[j]

                if d_out[j] <= params.exit_daily_rate:
                    reason = "rate"
                    break

                if times[j] - times[k] >= max_hold:
                    reason = "max_hold"
                    break

            trades.append(CarryTrade(symbol, times[k], times[j], funding, reason))
            k = j + 1

        else:
            k += 1

    return trades


def trade_returns(trades: Sequence[CarryTrade], params: CarryParams, cost_multiplier: float = 1.0) -> List[float]:
    """Net return on capital of each trade."""

    cost = params.round_trip_cost * cost_multiplier

    return [(t.funding - cost) / params.capital_factor for t in trades]


def annual_return(trades: Sequence[CarryTrade], params: CarryParams, cost_multiplier: float = 1.0) -> float:
    """Time-weighted net return on capital while invested, per year."""

    days = sum((t.exit_ms - t.entry_ms) / DAY_MS for t in trades)

    if days <= 0:
        return 0.0

    return sum(trade_returns(trades, params, cost_multiplier)) / days * YEAR_DAYS


def year_of(ms: int) -> int:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).year


def by_year(trades: Sequence[CarryTrade], params: CarryParams) -> Dict[int, List[float]]:
    """{calendar year of the exit: [number of trades, pooled net return on capital]}."""

    out: Dict[int, List[float]] = {}

    for t, r in zip(trades, trade_returns(trades, params)):
        entry = out.setdefault(year_of(t.exit_ms), [0, 0.0])
        entry[0] += 1
        entry[1] += r

    return out


def judge(trades: Sequence[CarryTrade], params: CarryParams, rules: Dict) -> Dict:
    """The five registered conditions. Returns {"checks": [(text, value, passed)], "passed": bool}."""

    returns = trade_returns(trades, params)
    years = by_year(trades, params)
    counted = {y: v for y, v in years.items() if v[0] >= rules["min_year_trades"]}
    positive = sum(1 for v in counted.values() if v[1] > 0)
    share = positive / len(counted) if counted else 0.0
    bad = sum(1 for r in returns if r < -rules["bad_trade_loss"]) / len(returns) if returns else 1.0
    a1 = annual_return(trades, params)
    a2 = annual_return(trades, params, 2.0)

    checks = [
        (f"1. trades >= {rules['min_trades']}", f"{len(trades)}", len(trades) >= rules["min_trades"]),
        (f"2. net return on capital while invested >= {rules['min_annual_return'] * 100:.0f}% per year",
         f"{a1 * 100:+.2f}%", a1 >= rules["min_annual_return"]),
        (f"3. same at 2x costs >= {rules['min_annual_return_2x_costs'] * 100:.0f}% per year",
         f"{a2 * 100:+.2f}%", a2 >= rules["min_annual_return_2x_costs"]),
        (f"4. years with pooled net P&L > 0 >= {rules['min_positive_year_share'] * 100:.0f}% "
         f"(of years with >= {rules['min_year_trades']} trades)",
         f"{positive} of {len(counted)}", bool(counted) and share >= rules["min_positive_year_share"]),
        (f"5. trades losing more than {rules['bad_trade_loss'] * 100:.1f}% of capital <= {rules['max_bad_trade_share'] * 100:.0f}%",
         f"{bad * 100:.1f}%", bad <= rules["max_bad_trade_share"]),
    ]

    return {"checks": checks, "passed": all(c[2] for c in checks)}
