"""
Falcon AI

Probability Rule Registry

Version: 3.0.0
"""

import inspect
import pkgutil
import importlib

from .base import ProbabilityRule


class RuleRegistry:

    def __init__(self):

        self._rules = []

        self._discover()

    def _discover(self):

        package = importlib.import_module(
            "src.analysis.probability.rules"
        )

        for _, module_name, _ in pkgutil.iter_modules(
            package.__path__
        ):

            if module_name in (
                "__init__",
                "base",
                "registry",
            ):
                continue

            module = importlib.import_module(
                f"{package.__name__}.{module_name}"
            )

            for _, obj in inspect.getmembers(
                module,
                inspect.isclass,
            ):

                if (
                    issubclass(
                        obj,
                        ProbabilityRule,
                    )
                    and obj is not ProbabilityRule
                ):

                    self._rules.append(obj())

    def all(self):

        return self._rules