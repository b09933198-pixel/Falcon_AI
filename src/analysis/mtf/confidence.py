"""
Falcon AI

MTF Confidence Engine

Version: 1.0.0
"""

from __future__ import annotations


class ConfidenceFusion:

    def merge(

        self,

        confidences,

        weights,

    ):

        total = sum(weights)

        score = 0.0

        for confidence, weight in zip(

            confidences,

            weights,

        ):

            score += confidence * weight

        return score / total