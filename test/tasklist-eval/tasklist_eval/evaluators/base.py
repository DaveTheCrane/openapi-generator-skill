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

    ``plugin_group`` names the plugin folder the evaluator was loaded from
    (e.g. ``"openapi-generator"``). The plugin loader fills it in; evaluators
    normally leave it empty.
    """

    id: str = ""
    kind: EvaluatorKind = EvaluatorKind.BINARY
    description: str = ""
    plugin_group: str = ""

    @abstractmethod
    def evaluate(self, tasklist: TaskList, config) -> EvaluationResult:
        """Evaluate *tasklist* and return a structured result."""
        raise NotImplementedError
