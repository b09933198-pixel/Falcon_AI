"""
Tests for the daily forward run and the sheet text (fake exchange, synthetic candles).
"""

from src.analysis.volatility.excursion import excursion_targets
from src.analysis.volatility.risksheet import Sheet
from src.forward import ForwardStore
from src.forward.format import format_sheet_fa
from src.forward.runner import DAY_MS, merge_sources, run_symbol
from tests.validation.test_excursion import HOUR, mk, synthetic

SMALL = dict(rank_window=1500, min_level_rows=100)
ALL = synthetic(9400, seed=21)
ARCHIVE = ALL[:9000]


def exchange(upto, start=8800, hole=None):
    """Candles the fake exchange returns: indexes start..upto (inclusive), optionally with one missing."""

    return lambda: [c for k, c in enumerate(ALL[start:upto + 1], start) if k != hole]


def now_after(index):
    """A clock reading 10 minutes after candle `index` closed."""
    return ALL[index].timestamp + HOUR + 600_000


def test_merge_sources_prefers_the_archive():
    archive = ALL[:100]
    exchange_candles = [mk(c.timestamp, c.open, c.high + 5, c.low, c.close) for c in ALL[90:120]]
    merged = merge_sources(archive, exchange_candles)
    assert len(merged) == 120 and merged[95] == ALL[95] and merged[100].timestamp == ALL[100].timestamp
    assert merge_sources([], exchange_candles) == exchange_candles


def test_first_run_publishes_the_last_24_sheets_and_nothing_resolves():
    store = ForwardStore(":memory:")
    s = run_symbol(store, "BTCUSDT", ARCHIVE, exchange(9239), now_after(9239), **SMALL)

    assert s.refit and s.added == 24 and s.late == 0 and s.duplicates == 0 and s.no_history == 0
    assert s.outcomes_ok == 0 and s.pending == 24 and not s.warnings
    assert s.last_closed_open_ms == ALL[9239].timestamp
    assert s.latest_sheet is not None and s.latest_sheet.decision_open_ms == ALL[9239].timestamp
    assert [r["decision_open_ms"] for r in store.sheets("BTCUSDT", "1h")] == [c.timestamp for c in ALL[9216:9240]]
    assert store.latest_model("BTCUSDT", "1h") is not None


def test_running_twice_changes_nothing_and_the_model_is_reused():
    store = ForwardStore(":memory:")
    run_symbol(store, "BTCUSDT", ARCHIVE, exchange(9239), now_after(9239), **SMALL)
    before = store.sheets("BTCUSDT", "1h")
    s = run_symbol(store, "BTCUSDT", ARCHIVE, exchange(9239), now_after(9239) + 60_000, **SMALL)

    assert not s.refit and s.added == 0 and s.duplicates == 24 and s.new_candles == 0
    assert store.sheets("BTCUSDT", "1h") == before


def test_later_run_resolves_outcomes_exactly_like_the_backtest():
    store = ForwardStore(":memory:")
    run_symbol(store, "BTCUSDT", ARCHIVE, exchange(9239), now_after(9239), **SMALL)
    s = run_symbol(store, "BTCUSDT", ARCHIVE, exchange(9299), now_after(9299), **SMALL)

    assert s.outcomes_ok == 24 and s.outcomes_void == 0
    assert s.added == 24 and s.pending == 24                       # hours 9240-9275 were never logged: not backfilled

    targets = excursion_targets([ALL], horizon=24)                 # row k belongs to candle k + 167
    rows = {r["decision_open_ms"]: r for r in store.sheets("BTCUSDT", "1h")}
    for index in (9216, 9230, 9239):
        row = rows[ALL[index].timestamp]
        assert abs(row["outcome"] - targets[index - 167]) < 1e-12 and row["outcome_ms"] == now_after(9299)

    assert set(rows) == {c.timestamp for c in ALL[9216:9240]} | {c.timestamp for c in ALL[9276:9300]}


def test_a_hole_in_an_outcome_window_voids_the_sheet_and_nothing_is_repaired():
    store = ForwardStore(":memory:")
    run_symbol(store, "BTCUSDT", ARCHIVE, exchange(9239), now_after(9239), **SMALL)
    s = run_symbol(store, "BTCUSDT", ARCHIVE, exchange(9299, hole=9250), now_after(9299), **SMALL)

    rows = {r["decision_open_ms"]: r for r in store.sheets("BTCUSDT", "1h")}
    assert rows[ALL[9225].timestamp]["outcome"] is not None        # window 9226..9249 ends before the hole
    assert rows[ALL[9230].timestamp]["void"] == 1 and rows[ALL[9239].timestamp]["void"] == 1
    assert s.outcomes_void > 0 and s.no_history == 24               # new hours sit behind the hole: too little history


def test_changed_exchange_candles_are_reported_not_applied():
    store = ForwardStore(":memory:")
    run_symbol(store, "BTCUSDT", ARCHIVE, exchange(9239), now_after(9239), **SMALL)
    stored = store.candles("BTCUSDT", "1h")

    tampered = lambda: [mk(c.timestamp, c.open, c.high + 1, c.low, c.close) for c in ALL[9200:9240]]
    s = run_symbol(store, "BTCUSDT", ARCHIVE, tampered, now_after(9239) + 60_000, **SMALL)

    assert s.mismatches == 40 and any("differ" in w for w in s.warnings)
    assert store.candles("BTCUSDT", "1h") == stored


def test_model_is_refitted_after_90_days_and_stale_data_is_flagged():
    store = ForwardStore(":memory:")
    start = now_after(9239)
    run_symbol(store, "BTCUSDT", ARCHIVE, exchange(9239), start, **SMALL)
    s = run_symbol(store, "BTCUSDT", ARCHIVE, exchange(9239), start + 91 * DAY_MS, **SMALL)

    assert s.refit and any("old" in w for w in s.warnings)
    assert s.model_id.startswith("BTCUSDT-1h-")


def test_gap_between_archive_and_exchange_is_a_warning():
    store = ForwardStore(":memory:")
    s = run_symbol(store, "BTCUSDT", ARCHIVE, exchange(9239, start=9010), now_after(9239), **SMALL)
    assert any("gap between the archive" in w for w in s.warnings)


def test_sheet_text():
    sheet = Sheet(
        decision_open_ms=1792188000000, expected_range=0.0031,
        quantiles={0.5: 0.018, 0.8: 0.029, 0.95: 0.046}, rank=0.823, level="high", log_expected=-5.8,
    )
    text = format_sheet_fa("BTCUSDT", "1h", sheet, 81792.93, HOUR)
    assert "BTCUSDT" in text and "بالا" in text and "صدک 82" in text
    assert "0.31٪" in text and "1.80٪" in text and "2.90٪" in text and "4.60٪" in text
    assert "2026-10-16 23:00 UTC" in text and "81,793" in text
    assert "جهت قیمت پیش‌بینی نمی‌شود" in text
    assert "3,762" in text
