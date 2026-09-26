"""Abstract evaluator interface.

An evaluator inspects a parsed :class:`~tasklist_eval.models.TaskList` and
returns an :class:`~tasklist_eval.models.EvaluationResult`. Evaluators are kept
deliberately decoupled from the rest of the framework — they receive only a
``TaskList`` and the run config, and never import the runner or reporter.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from ..models import EvaluationResult, EvaluatorKind, TaskList


class Evaluator(ABC):
    """Base class for all evaluators.

    Subclasses set the class attributes ``id`` and ``kind`` (and optionally a
    short human-readable ``description``) and implement :meth:`evaluate`.
    """

    id: str = ""
    kind: EvaluatorKind = EvaluatorKind.BINARY
    description: str = ""

    @abstractmethod
    def evaluate(self, tasklist: TaskList, config) -> EvaluationResult:
        """Evaluate *tasklist* and return a structured result."""
        raise NotImplementedError
