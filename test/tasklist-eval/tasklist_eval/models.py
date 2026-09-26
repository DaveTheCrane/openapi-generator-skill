"""Core data models for the tasklist evaluation framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class Verdict(Enum):
    """The outcome verdict of an evaluator or an overall run."""

    PASS = "pass"
    FAIL = "fail"
    PARTIAL = "partial"


class EvaluatorKind(Enum):
    """Whether an evaluator produces a binary or a graded (0..1) result."""

    BINARY = "binary"
    GRADED = "graded"


@dataclass
class Task:
    """A single task parsed from a tasklist.

    Supports both the flat ``## Task N:`` style and the nested
    ``- [ ] N.M`` checkbox style. ``checkbox`` records the raw marker for
    completeness but is IGNORED when evaluators compute verdicts.
    """

    id: str | None
    title: str
    checkbox: str | None = None          # raw marker: " ", "x", "-", "~", or None
    optional: bool = False               # True when an optional `*` marker was present
    body_lines: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    children: list["Task"] = field(default_factory=list)

    def all_text(self) -> str:
        """Return title + body lines joined into a single string for scanning."""
        parts = [self.title]
        parts.extend(self.body_lines)
        return "\n".join(parts)

    def walk(self):
        """Yield this task and all descendant tasks (depth-first, pre-order)."""
        yield self
        for child in self.children:
            yield from child.walk()


@dataclass
class TaskList:
    """Parsed representation of a whole tasklist document."""

    title: str
    overview: str = ""
    tasks: list[Task] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    dependency_graph: dict | None = None
    raw: str = ""

    def iter_tasks(self):
        """Yield every task (top-level and nested) flattened via ``walk``."""
        for task in self.tasks:
            yield from task.walk()


@dataclass
class EvaluationResult:
    """The outcome of a single evaluator run against a tasklist."""

    evaluator_id: str
    kind: EvaluatorKind
    verdict: Verdict
    score: float | None                  # None for binary; 0.0–1.0 for graded
    summary: str
    evidence: list[str] = field(default_factory=list)
    details: dict = field(default_factory=dict)


@dataclass
class RunSummary:
    """Aggregated result of all evaluators in a single run."""

    tasklist_path: str
    results: list[EvaluationResult] = field(default_factory=list)
    overall_verdict: Verdict = Verdict.PASS
    duration_ms: int = 0
