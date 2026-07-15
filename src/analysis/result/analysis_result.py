from dataclasses import dataclass, field

from src.analysis.features import FeatureVector
from src.analysis.probability import Probability
from src.analysis.reasoning import ReasonCollection

from .metadata import AnalysisMetadata


@dataclass(slots=True)
class AnalysisResult:

    features: FeatureVector

    probability: Probability

    reasons: ReasonCollection

    metadata: AnalysisMetadata = field(
        default_factory=AnalysisMetadata
    )

    decision: object | None = None

    def as_dict(self):

        return {

            "features": self.features.as_dict(),

            "probability": self.probability.as_dict(),

            "reasons": self.reasons.as_dict(),

            "metadata": self.metadata.as_dict(),

            "decision": (
                self.decision.as_dict()
                if self.decision
                else None
            ),

        }