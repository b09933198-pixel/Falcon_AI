"""
Falcon AI

Multi Timeframe Collection

Version: 1.0.0
"""

from __future__ import annotations

from .snapshot import TimeframeSnapshot
from .timeframe import Timeframe


class TimeframeCollection:

    def __init__(self):

        self._items: dict[Timeframe, TimeframeSnapshot] = {}

    def add(
        self,
        snapshot: TimeframeSnapshot,
    ):

        self._items[snapshot.timeframe] = snapshot

    def get(
        self,
        timeframe: Timeframe,
    ):

        return self._items.get(timeframe)

    def all(self):

        return list(self._items.values())

    def __len__(self):

        return len(self._items)

    def as_dict(self):

        return {

            timeframe.value: snapshot.as_dict()

            for timeframe, snapshot in self._items.items()

        }