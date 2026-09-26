"""Evaluator registry.

A small id → evaluator-instance registry. The runner asks the registry for the
active evaluator set (all registered by default), or a subset selected by id via
the ``--evaluators`` config option. New evaluators can be added by calling
:func:`register` without touching the framework core.
"""

from __future__ import annotations

from .evaluators.base import Evaluator
from .evaluators.generated_code_usage import GeneratedCodeUsageEvaluator
from .evaluators.generator_in_pom import GeneratorInPomEvaluator
from .exceptions import ConfigError


class EvaluatorRegistry:
    """Maps evaluator ids to their instances."""

    def __init__(self) -> None:
        self._evaluators: dict[str, Evaluator] = {}

    def register(self, evaluator: Evaluator) -> None:
        """Register *evaluator* under its ``id``."""
        if not evaluator.id:
            raise ValueError("evaluator must define a non-empty id")
        self._evaluators[evaluator.id] = evaluator

    def ids(self) -> list[str]:
        """Return all registered evaluator ids."""
        return list(self._evaluators.keys())

    def descriptions(self) -> dict[str, str]:
        """Return an ``id -> description`` map for every registered evaluator.

        Evaluators that do not define a ``description`` map to an empty string.
        """
        return {
            eid: getattr(ev, "description", "") or ""
            for eid, ev in self._evaluators.items()
        }

    def get_all(self) -> list[Evaluator]:
        """Return every registered evaluator instance."""
        return list(self._evaluators.values())

    def get(self, ids: list[str]) -> list[Evaluator]:
        """Return the evaluators for *ids*, in the requested order.

        Raises
        ------
        ConfigError
            If any requested id is not registered.
        """
        unknown = [i for i in ids if i not in self._evaluators]
        if unknown:
            valid = ", ".join(sorted(self._evaluators))
            bad = ", ".join(unknown)
            raise ConfigError(
                f"unknown evaluator id(s): {bad}. Valid ids are: {valid}."
            )
        return [self._evaluators[i] for i in ids]

    def select(self, ids: list[str] | None) -> list[Evaluator]:
        """Return the selected evaluators, or all when *ids* is None."""
        if ids is None:
            return self.get_all()
        return self.get(ids)


def build_default_registry() -> EvaluatorRegistry:
    """Return a registry pre-populated with the built-in evaluators."""
    registry = EvaluatorRegistry()
    registry.register(GeneratorInPomEvaluator())
    registry.register(GeneratedCodeUsageEvaluator())
    return registry
