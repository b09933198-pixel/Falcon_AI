"""
Falcon AI

Test Runner

Version: 2.0.0
"""

import subprocess
import sys


TESTS = [

    "tests.unit.test_ema",
    "tests.integration.test_api",

    "tests.integration.test_market",

    "tests.integration.test_data",

    "tests.unit.test_indicator_base",

    "tests.unit.test_sma",

]


def run_test(module):

    print("=" * 60)
    print(module)
    print("=" * 60)

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            module
        ]
    )

    return result.returncode == 0


def main():

    print()
    print("=" * 60)
    print("FALCON AI TEST RUNNER")
    print("=" * 60)

    passed = 0

    for module in TESTS:

        if run_test(module):

            passed += 1

        else:

            print()
            print("FAILED :", module)
            return

    print()
    print("=" * 60)
    print("ALL TESTS PASSED")
    print(f"{passed}/{len(TESTS)}")
    print("=" * 60)


if __name__ == "__main__":
    main()