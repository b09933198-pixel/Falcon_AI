"""
Falcon AI

RSI Reference Validation

Version: 1.0.0
"""

from tests.reference.loader import ReferenceLoader


def main():

    print("=" * 60)
    print("RSI REFERENCE VALIDATION")
    print("=" * 60)

    rows = ReferenceLoader.load(
        "tests/reference/datasets/rsi_wilder.csv"
    )

    print()

    print("Dataset Loaded")

    print("Rows :", len(rows))

    print("First:", rows[0])

    print("Last :", rows[-1])


if __name__ == "__main__":
    main()