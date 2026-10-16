"""
Tests for the risk sheet model, the forward store and the outcome rules (F-008).

Synthetic candles only: they test the rules and the plumbing, not any market.
"""

import math

from src.analysis.volatility import build_table
from src.analysis.volatility.excursion import ExcursionModel, excursion_targets
from src.analysis.volatility.forecaster import VolatilityError
from src.analysis.volatility.risksheet import (
    SheetModel,
    feature_predictions,
    fit_sheet_model,
    make_sheets,
    split_contiguous,
)
from src.forward import ForwardStore, resolve_outcome
from tests.validation.test_excursion import HOUR, mk, raises, synthetic

FAST = dict(rank_window=1500, min_level_rows=100)


def fitted(n=9000, seed=11):
    candles = synthetic(n, seed=seed)
    return candles, fit_sheet_model([candles], HOUR, fit_ms=123, **FAST)


# ---------------- model ----------------

def test_model_round_trips_through_json():
    _, model = fitted()
    again = SheetModel.from_json(model.to_json())
    assert again == model
    assert len(model.ratios) == 4 and all(len(row) == 3 for row in model.ratios)
    assert model.cutoff_ms > 0 and model.train_rows > 5000


def test_feature_predictions_match_the_validated_forecaster():
    candles, model = fitted()
    table = build_table([candles], horizon=24)
    reference = ExcursionModel(HOUR, 24).fit_rows(table.columns, table.y, excursion_targets([candles], horizon=24))

    predictions = dict(feature_predictions(model, [candles]))
    for k in (400, 3000, 8500):
        window = candles[k - 167:k + 1]
        expected = reference.volatility.forecast(window).log_expected
        assert abs(predictions[candles[k].timestamp] - expected) < 1e-9


def test_sheets_are_ordered_and_use_the_level_of_their_rank():
    candles, model = fitted()
    opens = [c.timestamp for c in candles[-300:]]
    sheets = make_sheets(model, [candles], opens)

    assert len(sheets) == 300
    for sheet in sheets.values():
        q = sheet.quantiles
        assert 0 < q[0.5] < q[0.8] < q[0.95]
        assert sheet.level in ("low", "normal", "high", "extreme")
        expected_level = ("low" if sheet.rank < 0.25 else "normal" if sheet.rank < 0.75
                          else "high" if sheet.rank < 0.95 else "extreme")
        assert sheet.level == expected_level
        row = model.ratios[("low", "normal", "high", "extreme").index(sheet.level)]
        assert all(abs(q[level] - sheet.expected_range * r) < 1e-12 for level, r in zip((0.5, 0.8, 0.95), row))

    assert make_sheets(model, [candles], [candles[0].timestamp, -5]) == {}


def test_a_sheet_never_uses_anything_after_its_decision():
    candles, model = fitted()
    k = 7000
    full = make_sheets(model, [candles], [candles[k].timestamp])[candles[k].timestamp]
    cut = make_sheets(model, [candles[:k + 1]], [candles[k].timestamp])[candles[k].timestamp]
    assert full == cut


def test_split_contiguous():
    candles = synthetic(400, seed=1)
    assert len(split_contiguous(candles, HOUR)) == 1
    gapped = candles[:100] + candles[110:]
    parts = split_contiguous(gapped, HOUR)
    assert [len(p) for p in parts] == [100, 290]
    assert split_contiguous([], HOUR) == []
    assert raises(lambda: split_contiguous([candles[1], candles[0]], HOUR), VolatilityError)


# ---------------- outcome ----------------

def test_outcome_matches_the_backtest_definition():
    candles = synthetic(1500, seed=12)
    by_open = {c.timestamp: c for c in candles}
    targets = excursion_targets([candles], horizon=24)
    first_row = 167                                     # first candle with a full 168-candle past
    last_open = candles[-1].timestamp

    for offset in (0, 10, 500):
        i = first_row + offset
        status, value = resolve_outcome(by_open, candles[i].timestamp, HOUR, 24, last_open)
        assert status == "ok" and abs(value - targets[offset]) < 1e-12


def test_outcome_waits_until_the_window_is_closed_and_voids_on_a_hole():
    candles = synthetic(300, seed=13)
    by_open = {c.timestamp: c for c in candles}
    decision = candles[100].timestamp

    assert resolve_outcome(by_open, decision, HOUR, 24, decision + 23 * HOUR) == ("wait", None)
    assert resolve_outcome(by_open, decision, HOUR, 24, decision + 24 * HOUR)[0] == "ok"

    del by_open[decision + 7 * HOUR]
    assert resolve_outcome(by_open, decision, HOUR, 24, decision + 30 * HOUR) == ("void", None)
    assert resolve_outcome(by_open, decision, HOUR, 24, decision + 5 * HOUR) == ("wait", None)


# ---------------- store ----------------

def test_candles_are_never_overwritten():
    store = ForwardStore(":memory:")
    candles = synthetic(10, seed=2)
    assert store.add_candles("BTCUSDT", "1h", candles, 1) == (10, 0)
    assert store.add_candles("BTCUSDT", "1h", candles, 2) == (0, 0)

    changed = [mk(c.timestamp, c.open, c.high + 1, c.low, c.close) for c in candles[:3]]
    assert store.add_candles("BTCUSDT", "1h", changed, 3) == (0, 3)
    assert store.candles("BTCUSDT", "1h") == candles
    assert store.candles("ETHUSDT", "1h") == []


def sheet_args(decision, last_closed):
    return dict(
        symbol="BTCUSDT", interval="1h", decision_open_ms=decision, created_ms=999, model_id="m1",
        expected=0.01, q50=0.012, q80=0.018, q95=0.03, rank=0.4, level="normal",
        interval_ms=HOUR, horizon=24, last_closed_open_ms=last_closed,
    )


def test_late_sheets_are_refused_and_duplicates_are_not_overwritten():
    store = ForwardStore(":memory:")
    d = 1000 * HOUR

    assert store.add_sheet(**sheet_args(d, d)) == "added"
    assert store.add_sheet(**sheet_args(d, d + HOUR)) == "duplicate"
    assert store.add_sheet(**sheet_args(d + HOUR, d + 24 * HOUR)) == "added"      # window not complete at d+25h-1
    assert store.add_sheet(**sheet_args(d + 2 * HOUR, d + 26 * HOUR)) == "late"   # last candle of its window closed
    assert store.add_sheet(**sheet_args(d + 3 * HOUR, d + 100 * HOUR)) == "late"
    assert [row["decision_open_ms"] for row in store.sheets("BTCUSDT", "1h")] == [d, d + HOUR]


def test_outcome_and_void_are_written_once():
    store = ForwardStore(":memory:")
    d = 1000 * HOUR
    for k in range(3):
        store.add_sheet(**sheet_args(d + k * HOUR, d + k * HOUR))

    assert store.pending("BTCUSDT", "1h") == [d, d + HOUR, d + 2 * HOUR]
    store.set_outcome("BTCUSDT", "1h", d, 0.02, 5)
    store.set_outcome("BTCUSDT", "1h", d, 0.99, 6)                 # second write is ignored
    store.set_void("BTCUSDT", "1h", d + HOUR)
    store.set_outcome("BTCUSDT", "1h", d + HOUR, 0.5, 7)           # void sheets get no outcome
    store.set_void("BTCUSDT", "1h", d)                              # an answered sheet cannot become void

    rows = {row["decision_open_ms"]: row for row in store.sheets("BTCUSDT", "1h")}
    assert rows[d]["outcome"] == 0.02 and rows[d]["outcome_ms"] == 5 and rows[d]["void"] == 0
    assert rows[d + HOUR]["outcome"] is None and rows[d + HOUR]["void"] == 1
    assert store.pending("BTCUSDT", "1h") == [d + 2 * HOUR]


def test_models_are_kept_and_the_newest_is_returned():
    store = ForwardStore(":memory:")
    assert store.latest_model("BTCUSDT", "1h") is None
    store.save_model("a", "BTCUSDT", "1h", 100, 90, "{}")
    store.save_model("b", "BTCUSDT", "1h", 200, 190, '{"x": 1}')
    assert store.latest_model("BTCUSDT", "1h") == ("b", 200, 190, '{"x": 1}')
    assert store.latest_model("ETHUSDT", "1h") is None
    assert raises(lambda: store.save_model("a", "BTCUSDT", "1h", 1, 1, "{}"), Exception)
