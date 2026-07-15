from .result import MultiTimeframeResult


class MultiTimeframeResultBuilder:

    @staticmethod
    def build(

        probability,

        agreement,

        confidence,

        dominant_action,

        aligned,

    ):

        return MultiTimeframeResult(

            probability=probability,

            agreement=agreement,

            confidence=confidence,

            dominant_action=dominant_action,

            aligned=aligned,

        )