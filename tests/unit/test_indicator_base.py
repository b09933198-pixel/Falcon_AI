"""
Falcon AI

Indicator Base Test

Version: 1.0.0
"""

from src.indicators.base import Indicator


def main():

    print("=" * 60)
    print("INDICATOR BASE TEST")
    print("=" * 60)

    try:

        Indicator()

        print("FAILED ❌")

    except TypeError:

        print("SUCCESS ✅")
        print()
        print("Abstract class works correctly.")


if __name__ == "__main__":
    main()