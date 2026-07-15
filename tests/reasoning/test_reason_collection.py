from src.analysis.reasoning import Reason
from src.analysis.reasoning import ReasonCollection


def test_collection_add():

    rc = ReasonCollection()

    rc.add(

        Reason(

            id="ema",

            title="EMA",

            description="EMA Bullish",

            category="Trend",

            score=1,

            confidence=1,

            priority=1,

            source="Test",

        )

    )

    assert len(rc) == 1


def test_collection_unique():

    rc = ReasonCollection()

    reason = Reason(

        id="ema",

        title="EMA",

        description="EMA",

        category="Trend",

        score=1,

        confidence=1,

        priority=1,

        source="Test",

    )

    rc.add(reason)

    rc.add(reason)

    assert len(rc) == 1


def test_collection_sorted():

    rc = ReasonCollection()

    rc.add(

        Reason(

            id="b",

            title="B",

            description="",

            category="Trend",

            score=1,

            confidence=1,

            priority=5,

            source="Test",

        )

    )

    rc.add(

        Reason(

            id="a",

            title="A",

            description="",

            category="Trend",

            score=1,

            confidence=1,

            priority=1,

            source="Test",

        )

    )

    assert rc.sorted()[0].id == "a"