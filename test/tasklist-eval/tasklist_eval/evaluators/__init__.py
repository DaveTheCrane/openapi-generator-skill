"""Built-in evaluators for the tasklist evaluation framework.

Evaluators are decoupled from the framework: each receives only a parsed
``TaskList`` plus the run ``EvalConfig`` and returns an ``EvaluationResult``.

The generic building blocks — :class:`PatternSet`, :class:`BinaryEvaluator`,
:class:`GradedEvaluator` and :class:`Area` — let new, skill-specific
evaluators be defined declaratively from named regex sets.
"""

from .binary import BinaryEvaluator
from .graded import Area, GradedEvaluator
from .patterns import PatternSet, find_in_tasks

__all__ = [
    "Area",
    "BinaryEvaluator",
    "GradedEvaluator",
    "PatternSet",
    "find_in_tasks",
]
