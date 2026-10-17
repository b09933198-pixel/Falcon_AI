"""
Falcon AI

Forward Layer

Status report and evaluation of the forward test (F-008)

Version: 1.0.0

Everything before the evaluation date is DESCRIPTIVE and decides nothing. The formal
verdict (F1-F5, research/FINDINGS.md) is produced only when, for every asset, at least
120 days have passed AND at least 2000 sheets are completed. Definitions used here
(amendment 3 in the ledger): "days" = from the first sheet's decision to the newest
completed sheet's decision; F1-F5 are judged on each asset separately, pooled over risk
levels, and must hold on both assets.
"""

from __future__ import annotations

from bisect import bisect_left
from typing import Dict, List, Optional, Sequence

from src.analysis.volatility.excursion import QUANTILES, RISK_LEVELS, excursion_targets
from src.analysis.volatility.risksheet import split_contiguous
from src.validation.excursion_walkforward import baseline_quantiles, coverage_at, pinball_loss
from src.validation.volatility_test import future_mean, log_ranges, past_mean

DAY_MS = 86_400_000
MIN_DAYS = 120
MIN_COMPLETED = 2000
MIN_LEVEL_SHEETS = 300

F1 = (0.90, 0.99)
F2 = (0.72, 0.88)
F3 = (0.40, 0.60)
F4_MIN = 0.89


def row_stamps(segments: Sequence[Sequence], horizon: int = 24, fast: int = 24, slow: int = 168) -> List[int]:
    """Decision times of the rows excursion_targets creates (same rows, same order)."""

    out: List[int] = []

    for segment in segments:
        ranges = log_ranges(segment)
        a, b, c = past_mean(ranges, fast), past_mean(ranges, slow), future_mean(ranges, horizon)

        for i in range(len(segment)):
            if a[i] is None or b[i] is None or c[i] is None:
                continue
            out.append(segment[i].timestamp)

    return out


def _cov(values: Sequence[float], bounds: Sequence[float]) -> Optional[float]:
    return coverage_at(values, bounds) if values else None


def asset_stats(
    sheets: Sequence[Dict],
    candles: Sequence,
    interval_ms: int,
    horizon: int = 24,
    window_rows: int = 8_760,
    min_rows: int = 2_000,
) -> Dict:
    """All numbers of one asset. `candles` = archive + stored exchange candles (merged)."""

    out: Dict = {"sheets": len(sheets)}

    if not sheets:
        out.update(completed=0, void=0, open=0, days=0.0, logged_share=None, first_ms=None, last_done_ms=None)
        return out

    done = [s for s in sheets if s["outcome"] is not None and not s["void"]]
    first = sheets[0]["decision_open_ms"]
    last = sheets[-1]["decision_open_ms"]
    hours = (last - first) // interval_ms + 1
    last_done = done[-1]["decision_open_ms"] if done else None

    out.update(
        completed=len(done),
        void=sum(1 for s in sheets if s["void"]),
        open=sum(1 for s in sheets if s["outcome"] is None and not s["void"]),
        first_ms=first,
        last_done_ms=last_done,
        days=0.0 if last_done is None else (last_done - first) / DAY_MS,
        logged_share=len(sheets) / hours,
    )

    if not done:
        return out

    values = [s["outcome"] for s in done]
    out["coverage"] = {q: coverage_at(values, [s[f"q{int(q * 100)}"] for s in done]) for q in QUANTILES}

    levels = {}
    for name in RISK_LEVELS:
        part = [s for s in done if s["level"] == name]
        vals = [s["outcome"] for s in part]
        levels[name] = {"n": len(part), "q50": _cov(vals, [s["q50"] for s in part]),
                        "q80": _cov(vals, [s["q80"] for s in part]), "q95": _cov(vals, [s["q95"] for s in part])}
    out["levels"] = levels

    # outcomes recomputed from the stored candles, and baseline B on the same rows
    segments = split_contiguous(list(candles), interval_ms)
    stamps = row_stamps(segments, horizon)
    excursions = excursion_targets(segments, horizon)
    index = {t: k for k, t in enumerate(stamps)}

    out["unmatched"] = sum(1 for s in done if s["decision_open_ms"] not in index)
    out["recompute_mismatch"] = sum(
        1 for s in done
        if s["decision_open_ms"] in index and abs(excursions[index[s["decision_open_ms"]]] - s["outcome"]) > 1e-12
    )

    matched = [s for s in done if s["decision_open_ms"] in index]
    out["baseline"] = None

    if matched:
        start = index[matched[0]["decision_open_ms"]]

        try:
            base = baseline_quantiles(stamps, excursions, start, horizon * interval_ms, QUANTILES, window_rows, min_rows)
        except ValueError:
            base = None

        if base is not None:
            vals = [s["outcome"] for s in matched]
            sel = [index[s["decision_open_ms"]] - start for s in matched]
            res = {}
            for q in (0.80, 0.95):
                key = f"q{int(q * 100)}"
                res[q] = {
                    "model": pinball_loss(vals, [s[key] for s in matched], q),
                    "baseline": pinball_loss(vals, [base[q][k] for k in sel], q),
                    "baseline_coverage": coverage_at(vals, [base[q][k] for k in sel]),
                }
            out["baseline"] = res

    return out


def evaluable(stats: Dict) -> bool:
    return stats.get("completed", 0) >= MIN_COMPLETED and stats.get("days", 0.0) >= MIN_DAYS


def judge(stats: Dict) -> Dict[str, Optional[bool]]:
    """F1-F5 for one asset (None where it cannot be computed)."""

    cov = stats.get("coverage")
    if not cov:
        return {k: None for k in ("F1", "F2", "F3", "F4", "F5")}

    f4_levels = [v for v in stats["levels"].values() if v["n"] >= MIN_LEVEL_SHEETS]
    base = stats.get("baseline")

    return {
        "F1": F1[0] <= cov[0.95] <= F1[1],
        "F2": F2[0] <= cov[0.80] <= F2[1],
        "F3": F3[0] <= cov[0.50] <= F3[1],
        "F4": all(v["q95"] >= F4_MIN for v in f4_levels),
        "F5": None if base is None else all(base[q]["model"] < base[q]["baseline"] for q in (0.80, 0.95)),
    }


def _pct(x: Optional[float]) -> str:
    return "  -  " if x is None else f"{100 * x:5.1f}"


def render(all_stats: Dict[str, Dict]) -> str:
    """Plain-text report for all assets."""

    lines: List[str] = []

    for symbol, s in all_stats.items():
        lines.append("=" * 70)
        lines.append(f"{symbol}: {s['sheets']} sheets, {s['completed']} completed, {s['void']} void, {s['open']} open")

        if not s["sheets"]:
            continue

        lines.append(f"  days (first sheet -> newest completed): {s['days']:.1f} of {MIN_DAYS}; "
                     f"completed {s['completed']} of {MIN_COMPLETED}")
        lines.append(f"  logged share of hours between first and last sheet: {100 * s['logged_share']:.1f}%")

        if not s["completed"]:
            continue

        c = s["coverage"]
        lines.append(f"  coverage (all completed): q50 {_pct(c[0.5])}%  q80 {_pct(c[0.8])}%  q95 {_pct(c[0.95])}%"
                     "   (targets 50 / 80 / 95)")
        lines.append("  by level:        n    q50    q80    q95")

        for name, v in s["levels"].items():
            lines.append(f"    {name:8s} {v['n']:6d}  {_pct(v['q50'])}  {_pct(v['q80'])}  {_pct(v['q95'])}")

        if s["unmatched"] or s["recompute_mismatch"]:
            lines.append(f"  WARNING: {s['unmatched']} outcomes not found among stored candles, "
                         f"{s['recompute_mismatch']} differ from the recomputed value")

        b = s.get("baseline")
        if b:
            for q, v in b.items():
                lines.append(f"  pinball q{int(q * 100)}: model {v['model']:.6f}  baseline B {v['baseline']:.6f}  "
                             f"(B coverage {_pct(v['baseline_coverage'])}%)")
        else:
            lines.append("  baseline B: not computable yet")

    lines.append("=" * 70)

    if all(evaluable(s) for s in all_stats.values()):
        lines.append("EVALUATION DATE REACHED - formal verdict:")
        results = {sym: judge(s) for sym, s in all_stats.items()}
        for key in ("F1", "F2", "F3", "F4", "F5"):
            row = {sym: r[key] for sym, r in results.items()}
            ok = None if any(v is None for v in row.values()) else all(row.values())
            lines.append(f"  {key}: {'PASS' if ok else 'FAIL' if ok is False else 'n/a'}   " +
                         "  ".join(f"{sym} {'ok' if v else 'no' if v is False else 'n/a'}" for sym, v in row.items()))
    else:
        lines.append("DESCRIPTIVE ONLY: the evaluation date is not reached; nothing here is a verdict.")

    return "\n".join(lines)
