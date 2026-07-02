"""
Falcon AI

Reference Validator

Version: 1.0.0
"""


class ReferenceValidator:

    @staticmethod
    def compare(result, expected, tolerance=0.01):

        if len(result) != len(expected):
            return False

        for r, e in zip(result, expected):

            if r is None and e is None:
                continue

            if r is None or e is None:
                return False

            if abs(r - e) > tolerance:
                return False

        return True