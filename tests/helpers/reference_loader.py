"""
Falcon AI

Reference Dataset Loader

Version: 1.0.0
"""

from pathlib import Path
import csv


def load_csv(path: str):

    file = Path(path)

    with file.open(
        newline="",
        encoding="utf-8"
    ) as f:

        return list(csv.DictReader(f))