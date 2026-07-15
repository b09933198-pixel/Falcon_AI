from .decision import Decision


class DecisionBuilder:

    @staticmethod
    def build(

        action,

        confidence,

        score,

        reason,

        timeframe="Unknown",

        timestamp=0,

    ):

        return Decision(

            action=action,

            confidence=confidence,

            score=score,

            reason=reason,

            timeframe=timeframe,

            timestamp=timestamp,

        )