from src.analysis.mtf.agreement import AgreementEngine


def test_agreement():

    score = AgreementEngine().score(

        [

            "BUY",

            "BUY",

            "BUY",

            "SELL",

        ]

    )

    assert score == 0.75