"""
Tests for the forward-test report (synthetic candles and hand-built sheets).
"""

from src.analysis.volatility.excursion import excursion_targets
from src.analysis.volatility.risksheet import split_contiguous
from src.forward.report import asset_stats, evaluable, judge, render, row_stamps
from tests.validation.test_excursion import HOUR, synthetic

ALL = synthetic(4000, seed=5)
SEG = split_contiguous(ALL, HOUR)
STAMPS = row_stamps(SEG)
E = excursion_targets(SEG)
SMALL = dict(window_rows=1500, min_rows=300)


def sheets(lo, hi, q50=0.01, q80=0.02, q95=0.04, level="normal", void_at=()):
    out = []
    for k in range(lo, hi):
        out.append({"decision_open_ms": STAMPS[k], "created_ms": STAMPS[k], "model_id": "m", "expected": 0.01,
                    "q50": q50, "q80": q80, "q95": q95, "rank": 0.5, "level": level,
                    "outcome": None if k in void_at else E[k], "outcome_ms": 1, "void": 1 if k in void_at else 0})
    return out


def test_row_stamps_align_with_excursion_targets():
    assert len(STAMPS) == len(E) and STAMPS == sorted(STAMPS)


def test_coverage_extremes_and_counts():
    s = asset_stats(sheets(2500, 2900, q50=10.0, q80=10.0, q95=10.0), ALL, HOUR, **SMALL)
    assert s["completed"] == 400 and s["coverage"] == {0.5: 1.0, 0.8: 1.0, 0.95: 1.0}
    assert s["recompute_mismatch"] == 0 and s["unmatched"] == 0
    s = asset_stats(sheets(2500, 2900, q50=0.0, q80=0.0, q95=0.0), ALL, HOUR, **SMALL)
    assert s["coverage"] == {0.5: 0.0, 0.8: 0.0, 0.95: 0.0}
    assert s["levels"]["normal"]["n"] == 400 and s["levels"]["low"]["n"] == 0 and s["levels"]["low"]["q95"] is None


def test_tampered_outcome_is_detected_and_open_and_void_are_counted():
    data = sheets(2500, 2600, void_at=(2510,))
    data[3]["outcome"] += 0.01
    data[-1]["outcome"] = None
    s = asset_stats(data, ALL, HOUR, **SMALL)
    assert s["recompute_mismatch"] == 1 and s["void"] == 1 and s["open"] == 1 and s["completed"] == 98
    assert "WARNING" in render({"BTCUSDT": s})


def test_logged_share_and_days():
    data = sheets(2500, 2740)
    del data[10:34]                       # one missing day of hours
    s = asset_stats(data, ALL, HOUR, **SMALL)
    assert abs(s["logged_share"] - 216 / 240) < 1e-12
    assert abs(s["days"] - (STAMPS[2739] - STAMPS[2500]) / 86_400_000) < 1e-12


def test_baseline_pinball_and_empty_cases():
    s = asset_stats(sheets(2500, 2800), ALL, HOUR, **SMALL)
    b = s["baseline"]
    assert b[0.95]["model"] > 0 and b[0.95]["baseline"] > 0 and 0.0 <= b[0.8]["baseline_coverage"] <= 1.0
    empty = asset_stats([], ALL, HOUR)
    assert empty["sheets"] == 0 and not evaluable(empty) and "0 sheets" in render({"X": empty})


def test_evaluation_only_when_due_and_thresholds():
    s = asset_stats(sheets(2500, 2800), ALL, HOUR, **SMALL)
    assert not evaluable(s) and "DESCRIPTIVE ONLY" in render({"A": s})

    def stat(c95=0.95, c80=0.80, c50=0.5, lv=0.95, n=500, better=True):
        base = {q: {"model": 1.0 if better else 3.0, "baseline": 2.0, "baseline_coverage": 0.8} for q in (0.8, 0.95)}
        return {"coverage": {0.5: c50, 0.8: c80, 0.95: c95}, "baseline": base,
                "levels": {"low": {"n": n, "q95": lv}, "high": {"n": 10, "q95": 0.0}}}

    assert all(judge(stat()).values())
    assert not judge(stat(c95=0.899))["F1"] and judge(stat(c95=0.90))["F1"] and not judge(stat(c95=0.991))["F1"]
    assert not judge(stat(c80=0.719))["F2"] and not judge(stat(c80=0.881))["F2"] and judge(stat(c80=0.88))["F2"]
    assert not judge(stat(c50=0.399))["F3"] and not judge(stat(c50=0.601))["F3"]
    assert not judge(stat(lv=0.889))["F4"] and judge(stat(lv=0.89))["F4"]
    assert judge(stat(n=299, lv=0.0))["F4"]                    # level below 300 sheets is not judged
    assert not judge(stat(better=False))["F5"]
    assert judge({"coverage": None})["F1"] is None
