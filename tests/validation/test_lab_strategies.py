"""
Tests for the eight F-009 strategies: designed price paths where the answer is known, plus a causality test
(a signal at candle i must not change when later candles are removed) and the warm-up and conflict rules.
"""

import random

from src.lab.strategies import STRATEGIES, START, build_context
from tests.validation.test_excursion import HOUR, mk


def from_closes(closes, start_price=None):
    """Candles whose close path is given. Down candles: low = close - 0.2, high = open + 0.1; up candles:
    low = open - 0.1, high = close + 0.2; flat: +-0.2. Open = previous close."""

    out = []
    prev = closes[0] if start_price is None else start_price

    for k, c in enumerate(closes):
        o = prev

        if c < o:
            h, l = o + 0.1, c - 0.2
        elif c > o:
            h, l = c + 0.2, o - 0.1
        else:
            h, l = c + 0.2, c - 0.2

        out.append(mk(k * HOUR, o, h, l, c))
        prev = c

    return out


def path(points):
    """Piecewise-linear close path through (index, price) points."""

    closes = []

    for (i0, p0), (i1, p1) in zip(points, points[1:]):
        for t in range(i0, i1):
            closes.append(p0 + (p1 - p0) * (t - i0) / (i1 - i0))

    closes.append(points[-1][1])

    return closes


def run(name, candles):
    return STRATEGIES[name](build_context(candles))


def walk(n, seed, vol=0.004):
    rnd = random.Random(seed)
    out = []
    price = 100.0

    for k in range(n):
        o = price
        c = o * (1 + rnd.gauss(0, vol))
        h = max(o, c) * (1 + abs(rnd.gauss(0, vol / 3)))
        l = min(o, c) * (1 - abs(rnd.gauss(0, vol / 3)))
        out.append(mk(k * HOUR, o, h, l, c))
        price = c

    return out


def sig(s):
    return (s.index, s.direction, s.stop_level, s.target, s.target_price)


# ---------------- designed paths ----------------

def test_s14_donchian_breakout_long_and_short():
    closes = [100.0] * 250
    closes[230] = 102.0
    closes[231] = 100.0
    s = run("S14", from_closes(closes))
    assert [(x.index, x.direction) for x in s] == [(230, 1)]
    assert s[0].stop_level == min(from_closes(closes)[k].low for k in range(221, 231))
    closes = [100.0] * 250
    closes[240] = 98.0
    s = run("S14", from_closes(closes))
    assert [(x.index, x.direction) for x in s] == [(240, -1)] and abs(s[0].stop_level - 100.2) < 1e-9


def test_s16_liquidity_sweep_short_and_long():
    closes = [100.0] * 250
    c = from_closes(closes)
    c[230] = mk(230 * HOUR, 100.0, 101.0, 99.8, 100.1)         # wick above the 20-candle high, close back inside
    s = run("S16", c)
    assert [(x.index, x.direction, x.stop_level) for x in s] == [(230, -1, 101.0)]
    c = from_closes(closes)
    c[230] = mk(230 * HOUR, 100.0, 100.2, 99.0, 99.9)
    s = run("S16", c)
    assert [(x.index, x.direction, x.stop_level) for x in s] == [(230, 1, 99.0)]
    c = from_closes(closes)
    c[230] = mk(230 * HOUR, 100.0, 100.22, 99.8, 100.1)        # sweep too small (needs > 0.1 x ATR beyond the high)
    assert run("S16", c) == []


def test_s10_and_s12_match_a_naive_scan():
    for seed in (1, 2, 3):
        c = walk(900, seed, vol=0.01)
        ctx = build_context(c)
        r = ctx.rsi
        want = []
        for i in range(START, len(c)):
            if r[i - 1] < 30 <= r[i]:
                want.append((i, 1))
            if r[i - 1] > 70 >= r[i]:
                want.append((i, -1))
        assert [(x.index, x.direction) for x in run("S10", c)] == want
        e20, e50 = ctx.ema20, ctx.ema50
        want = []
        for i in range(START, len(c)):
            if e20[i - 1] <= e50[i - 1] and e20[i] > e50[i]:
                want.append((i, 1))
            if e20[i - 1] >= e50[i - 1] and e20[i] < e50[i]:
                want.append((i, -1))
        got = run("S12", c)
        assert [(x.index, x.direction) for x in got] == want
        assert all(x.target == "none" and x.timeout_b == 200 and x.exit_when is not None for x in got)
    assert any(run("S10", walk(900, s, vol=0.01)) for s in (1, 2, 3))


def test_s10_and_s12_rule_exits():
    c = walk(900, 1, vol=0.01)
    ctx = build_context(c)
    for x in run("S10", c):
        j = x.index + 5
        assert x.exit_when(j) == ((ctx.rsi[j] >= 50) if x.direction == 1 else (ctx.rsi[j] <= 50))
    for x in run("S12", c):
        for j in range(x.index + 1, min(x.index + 40, len(c))):
            cross_up = ctx.ema20[j - 1] <= ctx.ema50[j - 1] and ctx.ema20[j] > ctx.ema50[j]
            cross_down = ctx.ema20[j - 1] >= ctx.ema50[j - 1] and ctx.ema20[j] < ctx.ema50[j]
            assert x.exit_when(j) == (cross_down if x.direction == 1 else cross_up)


def test_s13_support_resistance_bounce_on_a_triangle_wave():
    closes = [100.0 + (t % 20 if t % 20 <= 10 else 20 - t % 20) for t in range(420)]
    s = run("S13", from_closes(closes))
    got = {x.index: x.direction for x in s}
    want = {}
    for i in range(START, 420):
        if i % 20 == 1:
            want[i] = 1
        if i % 20 == 11:
            want[i] = -1
    assert got == want
    ctx = build_context(from_closes(closes))
    first = [x for x in s if x.direction == 1][0]
    assert abs(first.stop_level - (99.8 - 0.5 * ctx.atr[first.index])) < 1e-9


def test_s15_squeeze_breakout():
    closes = []
    price = 100.0
    for t in range(100):
        closes.append(100.0 + (3.0 if t % 2 == 0 else -3.0))          # wide bands
    for t in range(170):
        closes.append(100.0 + (3.0 * 0.96 ** t) * (1 if t % 2 == 0 else -1))   # bands keep shrinking
    closes.append(104.0)                                              # breakout above the upper band
    c = from_closes(closes)
    ctx = build_context(c)
    b = len(closes) - 1
    s = run("S15", c)
    hit = [x for x in s if x.index == b]
    assert hit and hit[0].direction == 1 and abs(hit[0].stop_level - ctx.mid[b]) < 1e-12
    assert all(x.index >= START for x in s)


def test_s01_rising_trendline_break_gives_a_short():
    closes = [100.0 + 0.5 * t + (t % 20 if t % 20 <= 10 else 20 - t % 20) for t in range(271)]
    base = from_closes(closes)
    ctx = build_context(base)
    p1, p2 = 240, 260
    line = lambda x: ctx.l[p1] + (ctx.l[p2] - ctx.l[p1]) / 20 * (x - p1)
    closes[270] = line(270) - 5.0
    c = from_closes(closes)
    s = [x for x in run("S01", c) if x.index >= 245]
    assert [(x.index, x.direction) for x in s] == [(270, -1)]
    assert s[0].stop_level == max(c[k].high for k in range(261, 271))


def test_s05_double_top_and_double_bottom():
    top = path([(0, 100), (200, 100), (210, 110), (220, 104), (230, 110), (236, 105.2), (237, 102), (260, 102)])
    c = from_closes(top)
    s = run("S05", c)
    assert [(x.index, x.direction) for x in s] == [(237, -1)]
    neck = min(c[k].low for k in range(210, 231))
    depth = max(c[210].high, c[230].high) - neck
    assert s[0].target == "price" and abs(s[0].target_price - (neck - depth)) < 1e-9
    assert abs(s[0].stop_level - max(c[210].high, c[230].high)) < 1e-9
    bottom = [200.0 - p for p in top]
    c = from_closes(bottom)
    s = run("S05", c)
    assert [(x.index, x.direction) for x in s] == [(237, 1)]
    neck = max(c[k].high for k in range(210, 231))
    depth = neck - min(c[210].low, c[230].low)
    assert abs(s[0].target_price - (neck + depth)) < 1e-9 and abs(s[0].stop_level - min(c[210].low, c[230].low)) < 1e-9


# ---------------- general rules ----------------

def test_causality_no_early_signals_and_no_conflicts():
    for seed in (11, 12):
        full = walk(1100, seed)
        cut = full[:800]

        for name in STRATEGIES:
            a = run(name, full)
            b = run(name, cut)
            assert [sig(x) for x in a if x.index < 800] == [sig(x) for x in b], name
            assert all(x.index >= START for x in a), name
            assert len({x.index for x in a}) == len(a), name
            assert all(x.direction in (1, -1) for x in a)

    # every strategy produces something on some random walk (so the tests above are not vacuous)
    counts = {name: sum(len(run(name, walk(1500, s, vol=0.008))) for s in (21, 22, 23)) for name in STRATEGIES}
    assert counts["S10"] > 0 and counts["S12"] > 0 and counts["S14"] > 0 and counts["S16"] > 0, counts
