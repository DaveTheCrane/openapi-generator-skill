"""Generic, regex-driven binary evaluator.

A :class:`BinaryEvaluator` is configured declaratively with named
:class:`~tasklist_eval.evaluators.patterns.PatternSet` objects:

* ``require`` — every set must match in at least one task;
* ``forbid``  — no set may match in any task.

PASS iff both conditions hold, otherwise FAIL.
"""

from __future__ import annotations

from ..models import EvaluationResult, EvaluatorKind, TaskList, Verdict
from .base import Evaluator
from .patterns import PatternSet


class BinaryEvaluator(Evaluator):
    """PASS iff all ``require`` sets match somewhere and no ``forbid`` set does.

    ``summaries`` optionally maps outcome keys to summary strings:

    * ``"pass"``            — used on PASS;
    * ``"missing:<set>"``   — used when exactly that one required set is missing
      (and no forbid set matched);
    * ``"missing:all"``     — used when every required set is missing
      (and no forbid set matched);
    * ``"fail"``            — generic FAIL fallback.

    Any key not provided falls back to a generic text naming the missing and
    forbidden set names.
    """

    kind = EvaluatorKind.BINARY

    def __init__(
        self,
        id: str,
        description: str,
        require: list[PatternSet],
        forbid: list[PatternSet] | None = None,
        summaries: dict[str, str] | None = None,
    ) -> None:
        if not id:
            raise ValueError("BinaryEvaluator id must be non-empty")
        self.id = id
        self.description = description
        self.require = list(require)
        self.forbid = list(forbid or [])
        if not self.require and not self.forbid:
            raise ValueError(
                f"BinaryEvaluator '{id}' needs at least one require or forbid set"
            )
        self.summaries = dict(summaries or {})

    def evaluate(self, tasklist: TaskList, config) -> EvaluationResult:
        roles = [(ps, "require") for ps in self.require] + [
            (ps, "forbid") for ps in self.forbid
        ]
        sets: dict[str, dict] = {
            ps.name: {"matched": False, "role": role, "matches": []}
            for ps, role in roles
        }
        evidence: list[str] = []

        # Task order first, then set order — at most one match per set per task.
        for task in tasklist.iter_tasks():
            text = task.all_text()
            tid = task.id if task.id is not None else "?"
            for ps, role in roles:
                matched = ps.search(text)
                if matched is None:
                    continue
                entry = sets[ps.name]
                entry["matched"] = True
                entry["matches"].append({"task": tid, "text": matched})
                label = ps.name if role == "require" else f"{ps.name} (forbidden)"
                evidence.append(f"Task {tid}: {label} — matched '{matched}'")

        missing = [ps.name for ps in self.require if not sets[ps.name]["matched"]]
        forbidden_hits = [ps.name for ps in self.forbid if sets[ps.name]["matched"]]
        passed = not missing and not forbidden_hits

        if not evidence:
            evidence.append("No matches for any pattern set in any task.")

        return EvaluationResult(
            evaluator_id=self.id,
            kind=self.kind,
            verdict=Verdict.PASS if passed else Verdict.FAIL,
            score=None,
            summary=self._summary(passed, missing, forbidden_hits),
            evidence=evidence,
            details={
                "sets": sets,
                "missing": missing,
                "forbidden_hits": forbidden_hits,
            },
        )

    def _summary(
        self, passed: bool, missing: list[str], forbidden_hits: list[str]
    ) -> str:
        if passed:
            return self.summaries.get("pass", "All required pattern sets matched.")

        if not forbidden_hits and missing:
            if len(missing) == len(self.require) and "missing:all" in self.summaries:
                return self.summaries["missing:all"]
            if len(missing) == 1 and f"missing:{missing[0]}" in self.summaries:
                return self.summaries[f"missing:{missing[0]}"]

        if "fail" in self.summaries:
            return self.summaries["fail"]

        parts = []
        if missing:
            parts.append(f"missing required set(s): {', '.join(missing)}")
        if forbidden_hits:
            parts.append(f"forbidden set(s) matched: {', '.join(forbidden_hits)}")
        return "FAIL — " + "; ".join(parts) + "."
