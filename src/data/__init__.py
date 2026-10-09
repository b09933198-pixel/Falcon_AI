"""
Falcon AI

Data Layer
"""

__all__ = ["DataManager"]


def __getattr__(name):
    # Lazy import: the history repository must not depend on the network client
    # (and therefore on `requests`) just because the package was imported.
    if name == "DataManager":
        from .manager import DataManager

        return DataManager

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
