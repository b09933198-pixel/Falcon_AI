"""
Falcon AI

Feature Vector

Version: 1.0.0
"""

from dataclasses import dataclass, field

from .feature import Feature


@dataclass(slots=True)
class FeatureVector:

    features: list[Feature] = field(default_factory=list)

    def add(self, feature: Feature) -> None:
        self.features.append(feature)

    def get(self, name: str):

        for feature in self.features:

            if feature.name == name:
                return feature

        return None

    def as_dict(self) -> dict:

        return {
            feature.name: feature.value
            for feature in self.features
        }

    def __len__(self):

        return len(self.features)