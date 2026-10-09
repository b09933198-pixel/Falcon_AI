"""
Falcon AI

Market Structure Tracker

Version: 1.0.0

Turns confirmed swings into market structure, one swing at a time.

Rules (v1)
----------
1. Alternation: swings are kept as high, low, high, low... When two swings of
   the same kind arrive in a row, only the more extreme one is kept (the higher
   high or the lower low). On a tie the earlier swing is kept.
2. Labels: each kept swing is labelled against the previous kept swing of the
   same kind: HH / LH for highs, HL / LL for lows, EQ when equal, FIRST when
   there is no earlier swing of that kind.
3. Trend: BULLISH when the latest high is HH and the latest low is HL;
   BEARISH when the latest high is LH and the latest low is LL; UNKNOWN until
   two highs and two lows exist; RANGING otherwise.

Causality
---------
The tracker only ever sees the swings it is fed. Feed it swings in
confirmation order (never before Swing.confirmed_index) and its state at any
moment is exactly what was knowable at that moment.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Iterable, List, Optional, Tuple

from .structure_type import StructureType
from .swing import Swing
from .swing_detector import confirmed_swings


class SwingLabel(str, Enum):

    HH = "HH"
    LH = "LH"
    HL = "HL"
    LL = "LL"
    EQ = "EQ"
    FIRST = "FIRST"


@dataclass(frozen=True, slots=True)
class StructureSwing:

    swing: Swing
    label: SwingLabel


class StructureTracker:

    def __init__(self) -> None:

        self._sequence: List[StructureSwing] = []
        self._last_confirmed: Optional[int] = None

    @property
    def sequence(self) -> List[StructureSwing]:

        return list(self._sequence)

    def update(self, swing: Swing) -> None:

        if (
            self._last_confirmed is not None
            and swing.confirmed_index < self._last_confirmed
        ):
            raise ValueError("swings must be fed in confirmation order")

        self._last_confirmed = swing.confirmed_index

        seq = self._sequence

        if seq and seq[-1].swing.is_high == swing.is_high:

            last = seq[-1].swing

            more_extreme = (
                swing.price > last.price
                if swing.is_high
                else swing.price < last.price
            )

            if not more_extreme:
                return

            seq.pop()

        seq.append(StructureSwing(swing, self._label(swing)))

    def _label(self, swing: Swing) -> SwingLabel:

        previous = None

        for item in reversed(self._sequence):
            if item.swing.is_high == swing.is_high:
                previous = item.swing
                break

        if previous is None:
            return SwingLabel.FIRST

        if swing.price == previous.price:
            return SwingLabel.EQ

        if swing.is_high:
            return SwingLabel.HH if swing.price > previous.price else SwingLabel.LH

        return SwingLabel.HL if swing.price > previous.price else SwingLabel.LL

    @property
    def trend(self) -> StructureType:

        last_high = None
        last_low = None

        for item in reversed(self._sequence):

            if item.swing.is_high and last_high is None:
                last_high = item

            elif not item.swing.is_high and last_low is None:
                last_low = item

            if last_high is not None and last_low is not None:
                break

        if last_high is None or last_low is None:
            return StructureType.UNKNOWN

        if SwingLabel.FIRST in (last_high.label, last_low.label):
            return StructureType.UNKNOWN

        if last_high.label == SwingLabel.HH and last_low.label == SwingLabel.HL:
            return StructureType.BULLISH

        if last_high.label == SwingLabel.LH and last_low.label == SwingLabel.LL:
            return StructureType.BEARISH

        return StructureType.RANGING


def structure_at(swings: Iterable[Swing], index: int) -> StructureTracker:
    """Structure as it was knowable when standing at candle `index`."""

    tracker = StructureTracker()

    for swing in confirmed_swings(list(swings), index):
        tracker.update(swing)

    return tracker


def structure_timeline(swings: Iterable[Swing]) -> List[Tuple[int, StructureType]]:
    """(confirmed_index, trend) after each swing, in confirmation order."""

    tracker = StructureTracker()
    timeline: List[Tuple[int, StructureType]] = []

    for swing in swings:
        tracker.update(swing)
        timeline.append((swing.confirmed_index, tracker.trend))

    return timeline


def trend_at(timeline: List[Tuple[int, StructureType]], index: int) -> StructureType:
    """Trend knowable at candle `index`, looked up in a timeline."""

    low, high = 0, len(timeline)

    while low < high:

        mid = (low + high) // 2

        if timeline[mid][0] <= index:
            low = mid + 1
        else:
            high = mid

    return timeline[low - 1][1] if low else StructureType.UNKNOWN
