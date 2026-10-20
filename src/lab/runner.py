"""
Falcon AI

Strategy Lab

Runs the F-009 strategies on candle segments: timeframe aggregation, hold-out window, pooled trades, report text.

Version: 1.0.0

The timeframe is data (config/lab.json), not code. Higher timeframes are built from the 1h archive; a timeframe
shorter than the base candles cannot be built.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, List, Optional, Sequence, Tuple

from src.domain.models import Candle
from src.lab.engine import Costs, Signal, Trade, simulate, summarize
from src.lab.strategies import NAMES, STRATEGIES, build_context
from src.analysis.volatility.risksheet import split_contiguous

BASE_MS = 3_600_000
SCALES = (0.5, 2.0)
REGISTERED = {"1h": "F-009"}


def parse_utc(text: str) -> int:
    return int(datetime.strptime(text, "%Y-%m-%d %H:%M").replace(tzinfo=timezone.utc).timestamp() * 1000)


def utc(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def aggregate(candles: Sequence[Candle], factor: int, base_ms: int = BASE_MS) -> List[Candle]:
    """Merge `factor` base candles into one. Buckets are aligned to the UTC epoch; only complete buckets are kept."""

    if factor < 1:
        raise ValueError("factor must be >= 1")

    if factor == 1:
        return list(candles)

    span = factor * base_ms
    buckets: Dict[int, List[Candle]] = {}

    for c in candles:
        buckets.setdefault(c.timestamp - c.timestamp % span, []).append(c)

    out: List[Candle] = []

    for start in sorted(buckets):
        group = buckets[start]

        if len(group) != factor or any(group[k].timestamp != start + k * base_ms for k in range(factor)):
            continue

        out.append(Candle(
            timestamp=start, open=group[0].open, high=max(c.high for c in group), low=min(c.low for c in group),
            close=group[-1].close, volume=sum(c.volume for c in group), quote_volume=sum(c.quote_volume for c in group),
            trades=sum(c.trades for c in group), buy_volume=sum(c.buy_volume for c in group),
            buy_quote_volume=sum(c.buy_quote_volume for c in group),
        ))

    return out


def timeframe_factor(timeframe: str, interval_to_ms) -> int:
    tf = interval_to_ms(timeframe)

    if tf < BASE_MS or tf % BASE_MS:
        raise ValueError(f"{timeframe} cannot be built from 1h candles")

    return tf // BASE_MS


def check_registered(timeframe: str, registration: Optional[str], findings_text: str) -> str:
    """The registration id that covers this timeframe, or ValueError. F-009 covers 1h only."""

    if registration is None:
        if timeframe in REGISTERED:
            return REGISTERED[timeframe]
        raise ValueError(f"timeframe {timeframe} is not part of a registered test; register it first (new F-0xx)")

    marker = f"## {registration}"
    pos = findings_text.find(marker)

    if pos < 0:
        raise ValueError(f"{registration} is not in research/FINDINGS.md")

    end = findings_text.find("\n## ", pos + 1)
    section = findings_text[pos:end if end > 0 else len(findings_text)]

    if timeframe not in section:
        raise ValueError(f"{registration} does not name the timeframe {timeframe}")

    return registration


@dataclass(frozen=True)
class Row:
    symbol: str
    entry_ms: int
    exit_ms: int
    trade: Trade


class Lab:
    """Strategies over several symbols. data[symbol] = (segments of candles at the working timeframe, funding)."""

    def __init__(self, data: Dict[str, Tuple[List[List[Candle]], Optional[Tuple[Sequence[int], Sequence[float]]]]],
                 tf_ms: int, start_ms: int):
        self.data = data
        self.tf_ms = tf_ms
        self.start_ms = start_ms
        self.contexts = {(sym, k): build_context(seg) for sym, (segs, _) in data.items() for k, seg in enumerate(segs)}
        self._signals: Dict[Tuple[str, int, str], List[Signal]] = {}

    def signals(self, symbol: str, k: int, name: str) -> List[Signal]:
        key = (symbol, k, name)

        if key not in self._signals:
            self._signals[key] = STRATEGIES[name](self.contexts[(symbol, k)])

        return self._signals[key]

    def windowed(self, symbol: str, k: int, name: str, window: str) -> List[Signal]:
        seg = self.data[symbol][0][k]
        keep = (lambda t: t >= self.start_ms) if window == "holdout" else (lambda t: t < self.start_ms)

        return [s for s in self.signals(symbol, k, name) if keep(seg[s.index].timestamp)]

    def signal_counts(self, name: str, window: str) -> Dict[str, int]:
        return {sym: sum(len(self.windowed(sym, k, name, window)) for k in range(len(segs)))
                for sym, (segs, _) in self.data.items()}

    def trades(self, name: str, gate: str, costs: Costs) -> Tuple[List[Row], Dict[str, int]]:

        rows: List[Row] = []
        skipped: Dict[str, int] = {}

        for sym, (segs, funding) in self.data.items():
            for k, seg in enumerate(segs):
                ctx = self.contexts[(sym, k)]
                found, sk = simulate(seg, ctx.atr, self.windowed(sym, k, name, "holdout"), gate, self.tf_ms, costs, funding)

                for key, value in sk.items():
                    skipped[key] = skipped.get(key, 0) + value

                rows += [Row(sym, seg[t.entry_index].timestamp, seg[t.exit_index].timestamp, t) for t in found]

        return rows, skipped


def run_all(lab: Lab, base: Costs, alpha: float, min_trades: int, min_win: float) -> Dict:
    """results[(strategy, gate)] = {summary, rows, skipped, sensitivity{scale: summary}}."""

    results: Dict = {}

    for name in STRATEGIES:
        for gate in ("A", "B"):
            rows, skipped = lab.trades(name, gate, base)
            entry = {
                "summary": summarize([r.trade for r in rows], gate, alpha, min_trades, min_win),
                "rows": rows, "skipped": skipped, "sensitivity": {},
                "by_symbol": {sym: _mean([r.trade.net_r for r in rows if r.symbol == sym]) for sym in lab.data},
                "long": sum(1 for r in rows if r.trade.direction == 1),
                "short": sum(1 for r in rows if r.trade.direction == -1),
            }

            for scale in SCALES:
                r2, _ = lab.trades(name, gate, Costs(base.fee, base.slippage, scale))
                entry["sensitivity"][scale] = summarize([r.trade for r in r2], gate, alpha, min_trades, min_win)

            results[(name, gate)] = entry

    return results


def _mean(values: Sequence[float]) -> Optional[float]:
    return sum(values) / len(values) if values else None


def _f(x: Optional[float], fmt: str) -> str:
    return "  -  " if x is None else format(x, fmt)


def render(results: Dict, meta: Dict) -> str:
    """Plain-text report. meta: timeframe, symbols, start_ms, end_ms, alpha, tests, costs, notes."""

    lines = [
        f"F-009 HOLD-OUT RESULT  timeframe {meta['timeframe']}  symbols {','.join(meta['symbols'])}",
        f"window {utc(meta['start_ms'])} .. {utc(meta['end_ms'])} UTC (seen once)",
        f"costs: taker {meta['fee'] * 100:.3f}% + slippage {meta['slippage'] * 100:.3f}% per side, plus funding",
        f"tests M = {meta['tests']}, alpha = {meta['alpha']:.5f} (one-sided), at least {meta['min_trades']} trades, win rate >= {meta['min_win'] * 100:.0f}%",
    ]
    lines += [f"note: {n}" for n in meta.get("notes", [])]

    passed = []

    for gate in ("A", "B"):
        lines += ["", f"Gate {gate}" + (" (fixed 1:1, 2 x ATR stop and target, timeout 48)" if gate == "A" else " (natural stop and target)"),
                  "  strategy                 trades  long/short   win%  breakeven%  meanR   p_binom   p_t     status"]

        for name in STRATEGIES:
            e = results[(name, gate)]
            s = e["summary"]

            if s["passed"]:
                passed.append(f"{name} gate {gate}")

            lines.append(
                f"  {name} {NAMES[name]:20s} {s['trades']:6d}  {e['long']:5d}/{e['short']:<5d}  "
                f"{_f(None if s['win_rate'] is None else s['win_rate'] * 100, '5.1f')}  "
                f"{_f(None if s['breakeven'] is None else s['breakeven'] * 100, '8.1f')}  "
                f"{_f(s['mean_r'], '+6.3f')}  {_f(s['p_binom'], '7.4f')}  {_f(s['p_t'], '7.4f')}  {s['status'].upper()}"
            )

            for scale, t in e["sensitivity"].items():
                lines.append(
                    f"        at {scale}x costs: win% {_f(None if t['win_rate'] is None else t['win_rate'] * 100, '5.1f')}"
                    f"  meanR {_f(t['mean_r'], '+6.3f')}"
                )

            sk = {k: v for k, v in e["skipped"].items() if v}
            sym = "  ".join(f"{k} meanR {_f(v, '+6.3f')}" for k, v in e["by_symbol"].items())
            lines.append(f"        by symbol: {sym}" + (f"   skipped: {sk}" if sk else ""))

    lines += ["", "PASSED: " + (", ".join(passed) if passed else "none"),
              "A strategy not listed under PASSED sends no signal."]

    return "\n".join(lines)


def trades_csv(results: Dict, tf_ms: int) -> str:
    out = ["strategy,gate,symbol,entry_utc,exit_utc,direction,entry,exit,stop_distance,gross_r,cost_r,net_r,reason"]

    for (name, gate), e in results.items():
        for r in e["rows"]:
            t = r.trade
            out.append(",".join(str(x) for x in (
                name, gate, r.symbol, utc(r.entry_ms), utc(r.exit_ms + tf_ms), t.direction, repr(t.entry), repr(t.exit),
                repr(t.stop_distance), repr(t.gross_r), repr(t.cost_r), repr(t.net_r), t.reason)))

    return "\n".join(out) + "\n"
