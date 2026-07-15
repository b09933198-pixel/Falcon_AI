"""
Falcon AI

Dataset Loader

Version: 1.0.0
"""

from pathlib import Path


DATASET_DIR = Path("tests/datasets")


def dataset(name: str):

    return DATASET_DIR / name