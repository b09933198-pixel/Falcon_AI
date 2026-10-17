"""
Falcon AI

Forward Layer

Daily run: fetch fresh candles, publish sheets for the newest closes, resolve old outcomes

Version: 1.0.0

One call of `run_symbol` does, for one symbol:
  1. store the newest COMPLETED exchange candles (never overwriting existing ones)
  2. build the candle series: archive history first, stored exchange candles after it
  3. load the model, or refit it when it is 90 days old
  4. publish a sheet for each of the last `horizon` closed candles (a sheet is refused when
     its outcome is already knowable, written once, never edited)
  5. fill in the outcome of every older sheet whose window is closed, or void it when the
     window has a hole

Sheets are computed from candles up to their own decision only (tested), so publishing a
sheet up to 23 hours after its decision cannot change its values. It is weaker than
real-time logging (part of the outcome window may already be visible to the logger);
this is disclosed in research/FINDINGS.md (F-008 amendment 2).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Callable, Dict, List, Optional, Sequence

from src.analysis.volatility.risksheet import (
    Sheet,
    SheetModel,
    fit_sheet_model,
    make_sheets,
    split_contiguous,
)
from src.domain.models import Candle
from src.forward.store import ForwardStore, resolve_outcome

DAY_MS = 86_400_000
REFIT_MS = 90 * DAY_MS
STALE_MS = 3 * 3_600_000


@dataclass
class RunSummary:
    symbol: str
    new_candles: int = 0
    mismatches: int = 0
    model_id: str = ""
    refit: bool = False
    added: int = 0
    duplicates: int = 0
    late: int = 0
    no_history: int = 0
    outcomes_ok: int = 0
    outcomes_void: int = 0
    pending: int = 0
    last_closed_open_ms: int = 0
    latest_sheet: Optional[Sheet] = None
    latest_close: float = 0.0
    warnings: List[str] = field(default_factory=list)


def merge_sources(archive: Sequence[Candle], exchange: Sequence[Candle]) -> List[Candle]:
    """Archive candles as they are, then exchange candles strictly after the last archive candle."""

    if not archive:
        return list(exchange)

    end = archive[-1].timestamp

    return list(archive) + [c for c in exchange if c.timestamp > end]


def utc_stamp(ms: int) -> str:
    return datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%d %H:%M")


def run_symbol(
    store: ForwardStore,
    symbol: str,
    archive: Sequence[Candle],
    fetch: Callable[[], Sequence[Candle]],
    now_ms: int,
    interval: str = "1h",
    interval_ms: int = 3_600_000,
    horizon: int = 24,
    rank_window: int = 8_760,
    min_level_rows: int = 300,
) -> RunSummary:

    summary = RunSummary(symbol)

    fresh = list(fetch())
    summary.new_candles, summary.mismatches = store.add_candles(symbol, interval, fresh, now_ms)

    if summary.mismatches:
        summary.warnings.append(f"{summary.mismatches} stored candles differ from the exchange now; stored values kept")

    combined = merge_sources(archive, store.candles(symbol, interval))

    if not combined:
        summary.warnings.append("no candles at all")
        return summary

    if archive:
        after = [c for c in combined if c.timestamp > archive[-1].timestamp]

        if after and after[0].timestamp != archive[-1].timestamp + interval_ms:
            summary.warnings.append("gap between the archive and the stored exchange candles")

    segments = split_contiguous(combined, interval_ms)
    last_closed = combined[-1].timestamp
    summary.last_closed_open_ms = last_closed
    summary.latest_close = combined[-1].close

    if now_ms - (last_closed + interval_ms) > STALE_MS:
        summary.warnings.append(f"newest candle is old: {utc_stamp(last_closed)} UTC")

    saved = store.latest_model(symbol, interval)

    if saved is None or now_ms - saved[1] >= REFIT_MS:
        model = fit_sheet_model(
            segments, interval_ms, fit_ms=now_ms, horizon=horizon,
            rank_window=rank_window, min_level_rows=min_level_rows,
        )
        model_id = f"{symbol}-{interval}-{datetime.fromtimestamp(now_ms / 1000, tz=timezone.utc):%Y%m%d}"
        store.save_model(model_id, symbol, interval, now_ms, model.cutoff_ms, model.to_json())
        summary.refit = True
    else:
        model_id, _, _, payload = saved
        model = SheetModel.from_json(payload)

    summary.model_id = model_id

    opens = [c.timestamp for c in combined[-horizon:]]
    sheets = make_sheets(model, segments, opens)

    for t in opens:

        sheet = sheets.get(t)

        if sheet is None:
            summary.no_history += 1
            continue

        status = store.add_sheet(
            symbol, interval, t, now_ms, model_id,
            sheet.expected_range, sheet.quantiles[0.5], sheet.quantiles[0.8], sheet.quantiles[0.95],
            sheet.rank, sheet.level, interval_ms, horizon, last_closed,
        )

        if status == "added":
            summary.added += 1
        elif status == "duplicate":
            summary.duplicates += 1
        else:
            summary.late += 1

    by_open: Dict[int, Candle] = {c.timestamp: c for c in combined}

    for t in store.pending(symbol, interval):

        state, value = resolve_outcome(by_open, t, interval_ms, horizon, last_closed)

        if state == "ok":
            store.set_outcome(symbol, interval, t, value, now_ms)
            summary.outcomes_ok += 1
        elif state == "void":
            store.set_void(symbol, interval, t)
            summary.outcomes_void += 1

    summary.pending = len(store.pending(symbol, interval))
    summary.latest_sheet = sheets.get(last_closed)

    return summary
