"""Generic, regex-driven graded evaluator.

A :class:`GradedEvaluator` scores a tasklist over a list of :class:`Area`
objects. Each area has a ``presence`` set (is this area in the tasklist at
all?) plus ``success`` and ``failure`` sets that classify it. Only the tasks
whose text matches ``presence`` are scanned for success/failure signals.

Classification per area:

* no presence hits                → ``absent`` (excluded from the score)
* success and failure both hit    → ``conflict_winner`` decides
* only success / only failure     → that label
* present but neither hit         → ``unmatched_present`` decides

Score = success areas / (success + failure areas). Verdict:
``score >= pass_threshold`` → PASS; ``0 < score < pass_threshold`` → PARTIAL;
``0`` → FAIL. With no in-scope areas the score is 0.0 and the verdict FAIL.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

from ..models import EvaluationResult, EvaluatorKind, TaskList, Verdict
from .base import Evaluator
from .patterns import PatternSet

Outcome = Literal["success", "failure"]


@dataclass
class Area:
    """A scored area: a presence set plus success/failure classifier sets."""

    name: str
    presence: PatternSet
    success: list[PatternSet] = field(default_factory=list)
    failure: list[PatternSet] = field(default_factory=list)


def _first_hit(sets: list[PatternSet], hits: list[tuple[str, str]]):
    """First ``(tid, text, set_name)`` over tasks in order, sets in order."""
    for tid, text in hits:
        for ps in sets:
            m = ps.search(text)
            if m is not None:
                return tid, m, ps.name
    return None


class GradedEvaluator(Evaluator):
    """Score the fraction of in-scope areas classified as success."""

    kind = EvaluatorKind.GRADED

    def __init__(
        self,
        id: str,
        description: str,
        areas: list[Area],
        success_label: str = "success",
        failure_label: str = "failure",
        conflict_winner: Outcome = "success",
        unmatched_present: Outcome = "failure",
        pass_threshold: float = 0.999,
    ) -> None:
        if not id:
            raise ValueError("GradedEvaluator id must be non-empty")
        if not areas:
            raise ValueError(f"GradedEvaluator '{id}' needs at least one area")
        for name, value in (
            ("conflict_winner", conflict_winner),
            ("unmatched_present", unmatched_present),
        ):
            if value not in ("success", "failure"):
                raise ValueError(f"{name} must be 'success' or 'failure', got {value!r}")
        if success_label == failure_label or "absent" in (success_label, failure_label):
            raise ValueError(
                "success_label and failure_label must differ and not be 'absent'"
            )
        self.id = id
        self.description = description
        self.areas = list(areas)
        self.success_label = success_label
        self.failure_label = failure_label
        self.conflict_winner = conflict_winner
        self.unmatched_present = unmatched_present
        self.pass_threshold = pass_threshold

    def _label(self, outcome: Outcome) -> str:
        return self.success_label if outcome == "success" else self.failure_label

    def evaluate(self, tasklist: TaskList, config) -> EvaluationResult:
        # Per-area (tid, text) for every task matching the area's presence set.
        area_hits: dict[str, list[tuple[str, str]]] = {a.name: [] for a in self.areas}
        for task in tasklist.iter_tasks():
            text = task.all_text()
            tid = task.id if task.id is not None else "?"
            for area in self.areas:
                if area.presence.search(text) is not None:
                    area_hits[area.name].append((tid, text))

        classifications: dict[str, str] = {}
        decided_by: dict[str, str | None] = {}
        evidence: list[str] = []

        for area in self.areas:
            hits = area_hits[area.name]
            if not hits:
                classifications[area.name] = "absent"
                decided_by[area.name] = None
                evidence.append(f"[{area.name}] absent — no relevant tasks found.")
                continue

            success_cite = _first_hit(area.success, hits)
            failure_cite = _first_hit(area.failure, hits)

            if success_cite and failure_cite:
                outcome: Outcome = self.conflict_winner
                cite = success_cite if outcome == "success" else failure_cite
            elif success_cite:
                outcome, cite = "success", success_cite
            elif failure_cite:
                outcome, cite = "failure", failure_cite
            else:
                outcome, cite = self.unmatched_present, None

            label = self._label(outcome)
            classifications[area.name] = label
            if cite is None:
                decided_by[area.name] = None
                evidence.append(
                    f"[{area.name}] {label} — area present but no success/failure "
                    "signal found."
                )
            else:
                tid, text, set_name = cite
                decided_by[area.name] = set_name
                evidence.append(
                    f"[{area.name}] {label} — Task {tid} matched '{text}' ({set_name})"
                )

        successes = [a for a, c in classifications.items() if c == self.success_label]
        failures = [a for a, c in classifications.items() if c == self.failure_label]
        in_scope = len(successes) + len(failures)

        if in_scope == 0:
            names = "/".join(a.name for a in self.areas)
            return EvaluationResult(
                evaluator_id=self.id,
                kind=self.kind,
                verdict=Verdict.FAIL,
                score=0.0,
                summary=f"No relevant areas found ({names}).",
                evidence=evidence,
                details={"areas": classifications, "score": 0.0, "decided_by": decided_by},
            )

        score = len(successes) / in_scope
        if score >= self.pass_threshold:
            verdict = Verdict.PASS
        elif score > 0:
            verdict = Verdict.PARTIAL
        else:
            verdict = Verdict.FAIL

        summary = (
            f"{len(successes)}/{in_scope} in-scope areas classified "
            f"{self.success_label} (score {score:.2f}). "
            f"{self.success_label}={sorted(successes)}, "
            f"{self.failure_label}={sorted(failures)}."
        )

        return EvaluationResult(
            evaluator_id=self.id,
            kind=self.kind,
            verdict=verdict,
            score=score,
            summary=summary,
            evidence=evidence,
            details={"areas": classifications, "score": score, "decided_by": decided_by},
        )
