"""
Tests for the strategy-lab runner: timeframe aggregation, the hold-out window, registration guard and the report.
"""

from src.lab.engine import Costs
from src.lab.runner import (
    Lab, aggregate, check_registered, parse_utc, render, run_all, timeframe_factor, trades_csv, utc,
)
from src.market.timeframe import interval_to_ms
from tests.validation.test_excursion import HOUR, mk
from tests.validation.test_lab_strategies import walk


def test_aggregate_ohlc_alignment_and_gaps():
    cs = [mk(k * HOUR, 10 + k, 12 + k, 9 + k, 11 + k) for k in range(8)]
    four = aggregate(cs, 4)
    assert [c.timestamp for c in four] == [0, 4 * HOUR]
    assert four[0].open == 10 and four[0].close == 14 and four[0].high == 15 and four[0].low == 9
    assert four[1].open == 14 and four[1].close == 18 and four[0].volume == 40.0 and four[0].trades == 4
    shifted = [mk((k + 1) * HOUR, 10, 11, 9, 10) for k in range(8)]          # starts at 01:00: first bucket incomplete
    assert [c.timestamp for c in aggregate(shifted, 4)] == [4 * HOUR]
    hole = [c for k, c in enumerate(cs) if k != 5]
    assert [c.timestamp for c in aggregate(hole, 4)] == [0]
    assert aggregate(cs, 1) == cs


def test_timeframe_factor_and_registration_guard():
    assert timeframe_factor("4h", interval_to_ms) == 4 and timeframe_factor("1d", interval_to_ms) == 24
    for bad in ("15m", "90m"):
        try:
            timeframe_factor(bad, interval_to_ms)
            assert False
        except ValueError:
            pass
    text = "## F-009 x\n1h only\n\n## F-010 later\nRound for 4h and 1d.\n\n## F-011 other\n15m"
    assert check_registered("1h", None, text) == "F-009"
    try:
        check_registered("4h", None, text)
        assert False
    except ValueError:
        pass
    assert check_registered("4h", "F-010", text) == "F-010"
    for tf, reg in (("1h", "F-010"), ("4h", "F-099")):
        try:
            check_registered(tf, reg, text)
            assert False
        except ValueError:
            pass


def test_holdout_window_pooling_and_report():
    a, b = walk(2600, 31, vol=0.008), walk(2600, 32, vol=0.008)
    start = a[1800].timestamp
    lab = Lab({"BTCUSDT": ([a], None), "ETHUSDT": ([b], None)}, HOUR, start)
    results = run_all(lab, Costs(), alpha=0.003125, min_trades=200, min_win=0.6)
    assert len(results) == 16
    total = 0

    for (name, gate), e in results.items():
        for r in e["rows"]:
            assert r.entry_ms >= start + HOUR - 1 and r.exit_ms >= r.entry_ms
        assert e["summary"]["trades"] == len(e["rows"]) == e["long"] + e["short"]
        assert set(e["sensitivity"]) == {0.5, 2.0}
        total += len(e["rows"])

    assert total > 0
    counts = lab.signal_counts("S14", "holdout")
    dev = lab.signal_counts("S14", "dev")
    assert set(counts) == {"BTCUSDT", "ETHUSDT"} and dev["BTCUSDT"] > 0 and counts["BTCUSDT"] > 0
    meta = {"registration": "F-009", "timeframe": "1h", "symbols": ["BTCUSDT", "ETHUSDT"], "start_ms": start, "end_ms": a[-1].timestamp,
            "fee": 0.0006, "slippage": 0.0002, "tests": 16, "alpha": 0.003125, "min_trades": 200, "min_win": 0.6,
            "notes": ["a note"]}
    text = render(results, meta)
    assert "Gate A" in text and "Gate B" in text and "PASSED: none" in text and "S16 Liquidity sweep" in text
    assert "F-009 HOLD-OUT RESULT" in text and "alpha = 0.0031" in text and "note: a note" in text
    csv = trades_csv(results, HOUR)
    assert csv.splitlines()[0].startswith("strategy,gate,symbol") and len(csv.splitlines()) == total + 1


def test_utc_helpers_round_trip():
    assert utc(parse_utc("2025-01-01 00:00")) == "2025-01-01 00:00" and parse_utc("1970-01-02 00:00") == 86_400_000
