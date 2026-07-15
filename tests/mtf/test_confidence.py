from src.analysis.mtf.confidence import ConfidenceFusion


def test_confidence():

    result = ConfidenceFusion().merge(

        [0.80, 0.90, 1.00],

        [1, 2, 3],

    )

    assert round(result, 2) == 0.93