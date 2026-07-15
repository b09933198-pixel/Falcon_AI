"""
Falcon AI

MTF Agreement Engine

Version: 1.0.0
"""

from __future__ import annotations


class AgreementEngine:

    def score(self, actions):

        if not actions:
            return 0.0

        counts = {}

        for action in actions:
            counts[action] = counts.get(action, 0) + 1

        majority = max(counts.values())

        return majority / len(actions)