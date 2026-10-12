"""
Falcon AI - F-005: does positioning / order-flow information predict direction? (read-only)

Seven pre-registered variants, two assets, built from the Binance USDT-M
derivatives archives (funding rate, open interest, long/short ratios, taker
buy/sell volume) and the spot taker-buy share. It trades nothing; edges are in
basis points BEFORE fees and are compared with an assumed round-trip cost. The
criteria are fixed in research/FINDINGS.md BEFORE the run and applied
mechanically here.

  D1  funding rate extreme (top / bottom 10 % of the last 90 days): +1 / -1, hold 24
  D2  open-interest surge (top 20 %), direction = sign of the last 24h return, hold 24
  D3  open-interest flush (bottom 20 %), direction = sign of the last 24h return, hold 24
  D4  futures taker flow (mean ln buy/sell ratio, 4h) top / bottom 10 %: +1 / -1, hold 4
  D5  spot taker-buy share (4h) top / bottom 10 %: +1 / -1, hold 4
  D6  global long/short account ratio top / bottom 10 %: +1 / -1, hold 24
  D7  top-trader long/short ratio top / bottom 10 %: +1 / -1, hold 24

Discovery uses decisions whose holding period ended by 2025-10-01. The hold-out
(2025-10-01 on) is evaluated ONLY for variants that pass C0-C3.

A variant PASSES the discovery part only if ALL hold:
  C0  at least 200 events on each asset
  C1  p < 0.05 / 7 on one asset and the same sign with p < 0.05 on the other
  C2  the sign holds in >= 70 % of usable years (>= 3 years with >= 20 events), both assets
  C3  the edge in its own direction is at least the assumed cost on both assets
and then in the hold-out:
  C4  the same sign on both assets and an edge of at least half the cost on both

Usage: python tools/check_positioning.py [SYMBOLS] [FLIPS]
       python tools/check_positioning.py BTCUSDT,ETHUSDT 2000
"""

import os
import sys
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.data.derivatives import DERIVATIVES_DB_PATH, DerivativesStore  # noqa: E402
from src.data.history import CandleRepository  # noqa: E402
from src.market.timeframe import interval_to_ms  # noqa: E402
from src.validation.positioning_scan import (  # noqa: E402
    Positioning,
    funding_feature,
    gated_direction,
    open_interest_change_feature,
    past_return_sign,
    percentile_signals,
    ratio_feature,
    spot_taker_feature,
    split_events,
    taker_flow_feature,
)
from src.validation.signal_scan import collect_events, evaluate_events  # noqa: E402

SYMBOLS = sys.argv[1].split(",") if len(sys.argv) > 1 else ["BTCUSDT", "ETHUSDT"]
FLIPS = int(sys.argv[2]) if len(sys.argv) > 2 else 2000

INTERVAL = "1h"
INTERVAL_MS = interval_to_ms(INTERVAL)
MIN_SEGMENT = 400

CUTOFF_MS = 1_759_276_800_000          # 2025-10-01 00:00 UTC
COST_BP = 12.0
HOLDOUT_MIN_BP = COST_BP / 2
MIN_EVENTS = 200
MIN_YEAR_SHARE = 0.70
MIN_YEARS = 3


_CACHE = {}


def features(name, candles, pos):
    """Feature series, computed once per (segment, symbol data, name)."""

    key = (id(candles), id(pos), name)

    if key not in _CACHE:
        _CACHE[key] = compute_feature(name, candles, pos)

    return _CACHE[key]


def compute_feature(name, candles, pos):

    if name == "funding":
        return funding_feature(candles, pos, INTERVAL_MS)
    if name == "oi":
        return open_interest_change_feature(candles, pos, INTERVAL_MS)
    if name == "taker":
        return taker_flow_feature(candles, pos, INTERVAL_MS)
    if name == "count_ls":
        return ratio_feature(candles, pos, "count_ls", INTERVAL_MS)
    if name == "top_ls":
        return ratio_feature(candles, pos, "top_ls", INTERVAL_MS)
    if name == "spot":
        return spot_taker_feature(candles, 4, INTERVAL_MS)

    raise ValueError(name)


def build(variant, candles, pos):
    """Signals of one variant for one segment."""

    if variant in ("D1", "D4", "D5", "D6", "D7"):
        name = {"D1": "funding", "D4": "taker", "D5": "spot", "D6": "count_ls", "D7": "top_ls"}[variant]
        return percentile_signals(features(name, candles, pos))

    oi = percentile_signals(features("oi", candles, pos), high=0.80, low=0.20)
    direction = past_return_sign(candles, 24, INTERVAL_MS)

    return gated_direction(oi, 1 if variant == "D2" else -1, direction)


VARIANTS = [
    ("D1 funding extreme", "D1", 24),
    ("D2 open-interest surge", "D2", 24),
    ("D3 open-interest flush", "D3", 24),
    ("D4 futures taker flow", "D4", 4),
    ("D5 spot taker-buy share", "D5", 4),
    ("D6 crowd long/short ratio", "D6", 24),
    ("D7 top-trader long/short", "D7", 24),
]

ALPHA = 0.05 / len(VARIANTS)


def sign(value):
    return (value > 0) - (value < 0)


def years_ok(result):
    return result.years_usable >= MIN_YEARS and result.years_same_sign / result.years_usable >= MIN_YEAR_SHARE


def try_evaluate(events):

    try:
        return evaluate_events(events, FLIPS)
    except ValueError:
        return None


def judge(first, second):

    if first is None or second is None:
        return False, False, False, False

    c0 = first.events >= MIN_EVENTS and second.events >= MIN_EVENTS
    same = sign(first.mean_edge) == sign(second.mean_edge) != 0
    c1 = same and any(
        a.p_value < ALPHA and b.p_value < 0.05 for a, b in ((first, second), (second, first))
    )
    c2 = years_ok(first) and years_ok(second)
    c3 = same and abs(first.mean_edge) >= COST_BP and abs(second.mean_edge) >= COST_BP

    return c0, c1, c2, c3


def main():

    if not DERIVATIVES_DB_PATH.exists():
        sys.exit(f"derivatives database not found: {DERIVATIVES_DB_PATH}")

    print(f"{','.join(SYMBOLS)} {INTERVAL}: {len(VARIANTS)} variants, p must be < {ALPHA:.4f} (0.05 / {len(VARIANTS)}, Bonferroni)")
    print(f"edges in bp before fees; assumed round-trip cost {COST_BP:.0f} bp; {FLIPS} block sign flips (weekly blocks)")
    print("discovery: holding period ends by 2025-10-01; the hold-out is shown only for variants that pass C0-C3")
    print()

    segments, positioning = {}, {}

    with CandleRepository() as repo:
        for symbol in SYMBOLS:
            segments[symbol] = [s for s in repo.segments(symbol, INTERVAL) if len(s) >= MIN_SEGMENT]

    with DerivativesStore() as store:
        for symbol in SYMBOLS:
            positioning[symbol] = Positioning.from_rows(store.funding(symbol), store.metrics(symbol))

    discovery, holdout = {}, {}

    for label, code, horizon in VARIANTS:

        for symbol in SYMBOLS:

            started = time.time()
            pos = positioning[symbol]
            events = collect_events(segments[symbol], lambda seg: build(code, seg, pos), horizon)
            first, second = split_events(events, CUTOFF_MS, horizon * INTERVAL_MS)
            result = try_evaluate(first)

            discovery[(label, symbol)] = result
            holdout[(label, symbol)] = second

            if result is None:
                print(f"{label:<28} {symbol[:3]} events {len(first):>5} (too few to evaluate)")
            else:
                print(
                    f"{label:<28} {symbol[:3]} events {result.events:>5} edge {result.mean_edge:+7.2f}bp "
                    f"hit {result.hit_rate * 100:4.1f}% p={result.p_value:.4f} yrs {result.years_same_sign}/{result.years_usable} "
                    f"({time.time() - started:.0f}s)"
                )

    print()
    print("=" * 70)

    passed = []

    if len(SYMBOLS) < 2:
        print("Only one symbol given: cross-asset criteria cannot be evaluated.")
    else:
        first, second = SYMBOLS[0], SYMBOLS[1]

        for label, _, _ in VARIANTS:

            c0, c1, c2, c3 = judge(discovery[(label, first)], discovery[(label, second)])
            ok = c0 and c1 and c2 and c3
            print(
                f"{label:<28} C0 events {'ok' if c0 else 'no'} | C1 p-value {'ok' if c1 else 'no'} "
                f"| C2 years {'ok' if c2 else 'no'} | C3 beats cost {'ok' if c3 else 'no'} -> {'PASS' if ok else 'fail'}"
            )

            if ok:
                passed.append(label)

    print("=" * 70)

    confirmed = []

    for label in passed:

        results = [try_evaluate(holdout[(label, s)]) for s in SYMBOLS[:2]]
        base = [discovery[(label, s)] for s in SYMBOLS[:2]]

        print(f"HOLD-OUT {label}:")
        for symbol, r in zip(SYMBOLS, results):
            if r is None:
                print(f"  {symbol[:3]}: too few events")
            else:
                print(f"  {symbol[:3]}: events {r.events} edge {r.mean_edge:+.2f}bp hit {r.hit_rate * 100:.1f}% p={r.p_value:.4f}")

        c4 = all(r is not None for r in results) and all(
            sign(r.mean_edge) == sign(b.mean_edge) and abs(r.mean_edge) >= HOLDOUT_MIN_BP
            for r, b in zip(results, base)
        )
        print(f"  C4 hold-out confirms: {'ok' if c4 else 'no'}")

        if c4:
            confirmed.append(label)

    if not passed:
        print("RESULT F-005: no positioning or order-flow signal passed the discovery criteria.")
    elif not confirmed:
        print("RESULT F-005: some variants passed discovery but none was confirmed in the hold-out.")
    else:
        for label in confirmed:
            print(f"CONFIRMED CANDIDATE: {label}")
        print("A confirmed candidate still needs forward (paper) testing with real fees before any use.")

    print("DONE")


main()
