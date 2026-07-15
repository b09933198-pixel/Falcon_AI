from src.analysis.reasoning import (
    Reason,
    ReasonCollection,
    ReasonEngine,
    ReasonType,
)


def test_engine_top():

    collection = ReasonCollection()

    collection.add(

        Reason(

            id="b",

            title="Second",

            description="",

            category=ReasonType.TREND,

            score=1,

            confidence=1,

            priority=2,

            source="Test",

        )

    )

    collection.add(

        Reason(

            id="a",

            title="First",

            description="",

            category=ReasonType.TREND,

            score=1,

            confidence=1,

            priority=1,

            source="Test",

        )

    )

    engine = ReasonEngine()

    top = engine.top(collection)

    assert top[0].id == "a"


def test_engine_summary():

    collection = ReasonCollection()

    collection.add(

        Reason(

            id="ema",

            title="EMA Bullish",

            description="",

            category=ReasonType.TREND,

            score=1,

            confidence=1,

            priority=1,

            source="Test",

        )

    )

    engine = ReasonEngine()

    summary = engine.summary(collection)

    assert summary == ["EMA Bullish"]