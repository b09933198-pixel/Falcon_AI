from .analysis_result import AnalysisResult
from .metadata import AnalysisMetadata


class AnalysisResultBuilder:

    @staticmethod
    def build(
        *,
        features,
        probability,
        reasons,
        symbol="",
        timeframe="",
        exchange="",
        timestamp=0,
    ):

        metadata = AnalysisMetadata(

            symbol=symbol,

            timeframe=timeframe,

            exchange=exchange,

            timestamp=timestamp,

        )

        return AnalysisResult(

            features=features,

            probability=probability,

            reasons=reasons,

            metadata=metadata,

        )