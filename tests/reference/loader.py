"""
Falcon AI

Reference Loader

Version: 1.0.0
"""

import csv


class ReferenceLoader:

    @staticmethod
    def load(path: str):

        rows = []

        with open(
            path,
            "r",
            newline="",
            encoding="utf-8"
        ) as file:

            reader = csv.DictReader(file)

            for row in reader:

                rows.append(row)

        return rows