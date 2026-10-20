"""
Falcon AI

Strategy Lab

The eight F-009 strategies, exactly as written in docs/STRATEGIES_F009.md

Version: 1.0.0

Each rule returns a list of Signal (see engine.py). The rules are written in candles, so they work on any
timeframe. A signal at candle i uses only candles 0..i (tested). No signal before candle index 200. If a long and a
short signal fall on the same candle, both are dropped.

Implementation choices where the document is open (reported with every result):
  - "20th percentile" of the squeeze rule = the value at sorted position int(0.2 * (120 - 1)) of the 120 bandwidths.
  - S05: H1 and H2 are the two most recent CONFIRMED pivot highs (lows) that follow each other.
  - S13: the level nearest to the close is taken among all support and resistance clusters; a support decides a
    long, a resistance a short.
  - Trendlines go through the wicks of the two most recent confirmed pivots (lows for a rising line, highs for a falling one).
"""

from __future__ import annotations

from bisect import bisect_left, bisect_right
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence

from src.lab.engine import Signal
from src.lab.indicators import atr_wilder, bollinger, ema, pivot_highs, pivot_lows, rsi_wilder

START = 200
PIVOT_W = 5


@dataclass
class Context:
    n: int
    o: List[float]
    h: List[float]
    l: List[float]
    c: List[float]
    atr: List[Optional[float]]
    rsi: List[Optional[float]]
    ema20: List[Optional[float]]
    ema50: List[Optional[float]]
    mid: List[Optional[float]]
    upper: List[Optional[float]]
    lower: List[Optional[float]]
    bw: List[Optional[float]]
    ph: List[int]
    pl: List[int]


def build_context(candles: Sequence) -> Context:

    o = [x.open for x in candles]
    h = [x.high for x in candles]
    l = [x.low for x in candles]
    c = [x.close for x in candles]
    mid, upper, lower, bw = bollinger(c, 20, 2.0)

    return Context(
        n=len(c), o=o, h=h, l=l, c=c,
        atr=atr_wilder(h, l, c, 14), rsi=rsi_wilder(c, 14), ema20=ema(c, 20), ema50=ema(c, 50),
        mid=mid, upper=upper, lower=lower, bw=bw,
        ph=pivot_highs(h, PIVOT_W), pl=pivot_lows(l, PIVOT_W),
    )


def _clean(signals: List[Signal]) -> List[Signal]:
    """Drop every signal that shares its candle with another one."""

    count: Dict[int, int] = {}

    for s in signals:
        count[s.index] = count.get(s.index, 0) + 1

    return sorted((s for s in signals if count[s.index] == 1), key=lambda s: s.index)


def _atr(ctx: Context, i: int) -> Optional[float]:
    a = ctx.atr[i]
    return a if a is not None and a > 0 else None


def _confirmed(pivots: List[int], i: int) -> List[int]:
    """Pivots known at candle i (k + 5 <= i)."""
    return pivots[:bisect_right(pivots, i - PIVOT_W)]


# ----------------------------------------------------------------------
# S01 trendline break
# ----------------------------------------------------------------------

def s01_trendline_break(ctx: Context) -> List[Signal]:

    out: List[Signal] = []

    for i in range(START, ctx.n):

        if _atr(ctx, i) is None:
            continue

        lows = _confirmed(ctx.pl, i)[-2:]

        if len(lows) == 2:
            p1, p2 = lows

            if ctx.l[p2] > ctx.l[p1] and i - p2 <= 100:
                slope = (ctx.l[p2] - ctx.l[p1]) / (p2 - p1)
                line = lambda x: ctx.l[p1] + slope * (x - p1)

                if all(ctx.c[x] >= line(x) for x in range(p2 + 1, i)) and ctx.c[i] < line(i) and ctx.c[i - 1] >= line(i - 1):
                    out.append(Signal(i, -1, stop_level=max(ctx.h[i - 9:i + 1])))

        highs = _confirmed(ctx.ph, i)[-2:]

        if len(highs) == 2:
            p1, p2 = highs

            if ctx.h[p2] < ctx.h[p1] and i - p2 <= 100:
                slope = (ctx.h[p2] - ctx.h[p1]) / (p2 - p1)
                line = lambda x: ctx.h[p1] + slope * (x - p1)

                if all(ctx.c[x] <= line(x) for x in range(p2 + 1, i)) and ctx.c[i] > line(i) and ctx.c[i - 1] <= line(i - 1):
                    out.append(Signal(i, 1, stop_level=min(ctx.l[i - 9:i + 1])))

    return _clean(out)


# ----------------------------------------------------------------------
# S05 double top / double bottom
# ----------------------------------------------------------------------

def s05_double_top_bottom(ctx: Context) -> List[Signal]:

    out: List[Signal] = []

    for i in range(START, ctx.n):

        a = _atr(ctx, i)

        if a is None:
            continue

        highs = _confirmed(ctx.ph, i)[-2:]

        if len(highs) == 2:
            k1, k2 = highs
            top = max(ctx.h[k1], ctx.h[k2])
            neck = min(ctx.l[k1:k2 + 1])
            depth = top - neck

            if (10 <= k2 - k1 <= 100 and abs(ctx.h[k1] - ctx.h[k2]) <= 0.5 * a and depth >= 2 * a
                    and 0 <= i - (k2 + PIVOT_W) <= 50 and ctx.c[i] < neck and ctx.c[i - 1] >= neck):
                out.append(Signal(i, -1, stop_level=top, target="price", target_price=neck - depth))

        lows = _confirmed(ctx.pl, i)[-2:]

        if len(lows) == 2:
            k1, k2 = lows
            bottom = min(ctx.l[k1], ctx.l[k2])
            neck = max(ctx.h[k1:k2 + 1])
            depth = neck - bottom

            if (10 <= k2 - k1 <= 100 and abs(ctx.l[k1] - ctx.l[k2]) <= 0.5 * a and depth >= 2 * a
                    and 0 <= i - (k2 + PIVOT_W) <= 50 and ctx.c[i] > neck and ctx.c[i - 1] <= neck):
                out.append(Signal(i, 1, stop_level=bottom, target="price", target_price=neck + depth))

    return _clean(out)


# ----------------------------------------------------------------------
# S10 RSI
# ----------------------------------------------------------------------

def s10_rsi(ctx: Context) -> List[Signal]:

    out: List[Signal] = []
    r = ctx.rsi

    for i in range(START, ctx.n):

        if _atr(ctx, i) is None or r[i] is None or r[i - 1] is None:
            continue

        if r[i - 1] < 30 and r[i] >= 30:
            out.append(Signal(i, 1, target="none", timeout_b=48, exit_when=lambda j: r[j] is not None and r[j] >= 50))
        elif r[i - 1] > 70 and r[i] <= 70:
            out.append(Signal(i, -1, target="none", timeout_b=48, exit_when=lambda j: r[j] is not None and r[j] <= 50))

    return _clean(out)


# ----------------------------------------------------------------------
# S12 EMA cross
# ----------------------------------------------------------------------

def s12_ema_cross(ctx: Context) -> List[Signal]:

    out: List[Signal] = []
    a, b = ctx.ema20, ctx.ema50

    def up(j: int) -> bool:
        return a[j - 1] is not None and b[j - 1] is not None and a[j - 1] <= b[j - 1] and a[j] > b[j]

    def down(j: int) -> bool:
        return a[j - 1] is not None and b[j - 1] is not None and a[j - 1] >= b[j - 1] and a[j] < b[j]

    for i in range(START, ctx.n):

        if _atr(ctx, i) is None or a[i] is None or b[i] is None:
            continue

        if up(i):
            out.append(Signal(i, 1, target="none", timeout_b=200, exit_when=down))
        elif down(i):
            out.append(Signal(i, -1, target="none", timeout_b=200, exit_when=up))

    return _clean(out)


# ----------------------------------------------------------------------
# S13 support / resistance bounce
# ----------------------------------------------------------------------

def _clusters(prices: List[float], gap: float) -> List[float]:
    """Means of groups of at least 3 prices where neighbouring sorted prices are at most `gap` apart."""

    out: List[float] = []
    group: List[float] = []

    for p in sorted(prices):
        if group and p - group[-1] > gap:
            if len(group) >= 3:
                out.append(sum(group) / len(group))
            group = []
        group.append(p)

    if len(group) >= 3:
        out.append(sum(group) / len(group))

    return out


def s13_support_resistance(ctx: Context) -> List[Signal]:

    out: List[Signal] = []

    for i in range(START, ctx.n):

        a = _atr(ctx, i)

        if a is None:
            continue

        lo, hi = i - 200, i - PIVOT_W
        lows = [ctx.l[k] for k in ctx.pl[bisect_left(ctx.pl, lo):bisect_right(ctx.pl, hi)]]
        highs = [ctx.h[k] for k in ctx.ph[bisect_left(ctx.ph, lo):bisect_right(ctx.ph, hi)]]
        found = [(abs(ctx.c[i] - s), s, "S") for s in _clusters(lows, 0.25 * a)]
        found += [(abs(ctx.c[i] - r), r, "R") for r in _clusters(highs, 0.25 * a)]

        if not found:
            continue

        _, level, kind = min(found)

        if kind == "S":
            if ctx.l[i] <= level + 0.1 * a and ctx.l[i] >= level - 0.5 * a and ctx.c[i] > level and ctx.c[i] > ctx.o[i]:
                out.append(Signal(i, 1, stop_level=level - 0.5 * a))
        else:
            if ctx.h[i] >= level - 0.1 * a and ctx.h[i] <= level + 0.5 * a and ctx.c[i] < level and ctx.c[i] < ctx.o[i]:
                out.append(Signal(i, -1, stop_level=level + 0.5 * a))

    return _clean(out)


# ----------------------------------------------------------------------
# S14 Donchian breakout
# ----------------------------------------------------------------------

def s14_donchian(ctx: Context) -> List[Signal]:

    out: List[Signal] = []

    for i in range(START, ctx.n):

        if _atr(ctx, i) is None:
            continue

        if ctx.c[i] > max(ctx.h[i - 20:i]):
            out.append(Signal(i, 1, stop_level=min(ctx.l[i - 9:i + 1])))
        elif ctx.c[i] < min(ctx.l[i - 20:i]):
            out.append(Signal(i, -1, stop_level=max(ctx.h[i - 9:i + 1])))

    return _clean(out)


# ----------------------------------------------------------------------
# S15 volatility squeeze breakout
# ----------------------------------------------------------------------

def s15_squeeze(ctx: Context) -> List[Signal]:

    out: List[Signal] = []
    bw = ctx.bw
    squeeze = [False] * ctx.n

    for k in range(119, ctx.n):
        window = bw[k - 119:k + 1]

        if any(v is None for v in window):
            continue

        squeeze[k] = bw[k] <= sorted(window)[int(0.2 * (len(window) - 1))]

    for i in range(START, ctx.n):

        if _atr(ctx, i) is None or not squeeze[i - 1] or ctx.upper[i] is None:
            continue

        if ctx.c[i] > ctx.upper[i]:
            out.append(Signal(i, 1, stop_level=ctx.mid[i]))
        elif ctx.c[i] < ctx.lower[i]:
            out.append(Signal(i, -1, stop_level=ctx.mid[i]))

    return _clean(out)


# ----------------------------------------------------------------------
# S16 liquidity sweep
# ----------------------------------------------------------------------

def s16_liquidity_sweep(ctx: Context) -> List[Signal]:

    out: List[Signal] = []

    for i in range(START, ctx.n):

        a = _atr(ctx, i)

        if a is None:
            continue

        top, bottom = max(ctx.h[i - 20:i]), min(ctx.l[i - 20:i])

        if ctx.h[i] > top + 0.1 * a and ctx.c[i] < top:
            out.append(Signal(i, -1, stop_level=ctx.h[i]))

        if ctx.l[i] < bottom - 0.1 * a and ctx.c[i] > bottom:
            out.append(Signal(i, 1, stop_level=ctx.l[i]))

    return _clean(out)


STRATEGIES: Dict[str, Callable[[Context], List[Signal]]] = {
    "S01": s01_trendline_break,
    "S05": s05_double_top_bottom,
    "S10": s10_rsi,
    "S12": s12_ema_cross,
    "S13": s13_support_resistance,
    "S14": s14_donchian,
    "S15": s15_squeeze,
    "S16": s16_liquidity_sweep,
}

NAMES = {
    "S01": "Trendline break", "S05": "Double top / bottom", "S10": "RSI", "S12": "EMA cross",
    "S13": "Support / resistance", "S14": "Donchian breakout", "S15": "Volatility squeeze", "S16": "Liquidity sweep",
}
