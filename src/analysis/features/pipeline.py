"""
Falcon AI

Enterprise Feature Pipeline

Version: 2.0.0
"""

from .feature import Feature
from .feature_vector import FeatureVector


class FeaturePipeline:

    def __init__(self):

        self.reset()

    def add(self, feature: Feature):

        self._validate(feature)

        self.vector.add(feature)

    def _validate(self, feature: Feature):

        if not feature.id:
            raise ValueError("Feature id is required")

        if not feature.name:
            raise ValueError("Feature name is required")

        if feature.weight < 0:
            raise ValueError("Weight cannot be negative")

        if not (0 <= feature.confidence <= 1):
            raise ValueError("Confidence must be between 0 and 1")

    def build(self):

        return self.vector

    def reset(self):

        self.vector = FeatureVector()