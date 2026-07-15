"""
Falcon AI

Reference Dataset Generator

Version: 1.0.0
"""

from pathlib import Path
import csv


class ReferenceGenerator:

    def load_close_prices(self, path: str):

        rows = []

        with open(path, newline="", encoding="utf-8") as f:

            reader = csv.DictReader(f)

            for row in reader:

                rows.append(float(row["Close"]))

        return rows


def main():

    dataset = (
        "tests/reference/datasets/"
        "rsi_wilder.csv"
    )

    generator = ReferenceGenerator()

    closes = generator.load_close_prices(dataset)

    print("=" * 60)
    print("REFERENCE GENERATOR")
    print("=" * 60)

    print()

    print("Rows :", len(closes))

    print("First:", closes[:5])

    print("Last :", closes[-5:])


if __name__ == "__main__":
    main()