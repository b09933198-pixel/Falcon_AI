"""
Falcon AI

Reason Collection

Version: 1.0.0
"""

from __future__ import annotations

from collections.abc import Iterator

from .reason import Reason


class ReasonCollection:

    def __init__(self):

        self._items: list[Reason] = []

    def add(self, reason: Reason) -> None:

        if any(r.id == reason.id for r in self._items):
            return

        self._items.append(reason)

    def remove(self, reason_id: str) -> None:

        self._items = [

            r

            for r in self._items

            if r.id != reason_id

        ]

    def clear(self) -> None:

        self._items.clear()

    def all(self) -> list[Reason]:

        return list(self._items)

    def sorted(self) -> list[Reason]:

        return sorted(

            self._items,

            key=lambda r: r.priority,

        )

    def top(self, n: int = 5) -> list[Reason]:

        return self.sorted()[:n]

    def as_dict(self):

        return [

            r.as_dict()

            for r in self.sorted()

        ]

    def __len__(self):

        return len(self._items)

    def __iter__(self) -> Iterator[Reason]:

        return iter(self._items)