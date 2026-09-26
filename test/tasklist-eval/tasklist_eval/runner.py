"""Evaluation runner — runs each evaluator and computes the overall verdict.

Overall verdict rules:

* A **binary** evaluator that FAILs makes the overall verdict FAIL.
* **Graded** evaluators are informational by default and do NOT change the
  overall verdict — UNLESS ``config.graded_threshold`` is set. When set, any
  graded score below the threshold turns that evaluator's verdict into FAIL and
  gates the overall verdict.
* Otherwise the overall verdict is PASS.

An exception raised by a single evaluator is caught and turned into a FAIL
result (with the error in its evidence) rather than aborting the whole run.
"""

from __future__ import annotations

import time

from .evaluators.base import Evaluator
from .models import EvaluationResult, EvaluatorKind, RunSummary, TaskList, Verdict


def _apply_threshold(result: EvaluationResult, threshold: float | None) -> EvaluationResult:
    """Downgrade a graded result to FAIL when it scores below *threshold*."""
    if (
        threshold is not None
        and result.kind is EvaluatorKind.GRADED
        and result.score is not None
        and result.score < threshold
    ):
        result.verdict = Verdict.FAIL
        result.summary = (
            f"{result.summary} (below graded threshold {threshold:.2f} → FAIL)"
        )
    return result


def _compute_overall(results: list[EvaluationResult], threshold: float | None) -> Verdict:
    """Return the overall verdict per the gating rules."""
    for r in results:
        if r.kind is EvaluatorKind.BINARY and r.verdict is Verdict.FAIL:
            return Verdict.FAIL
        if (
            r.kind is EvaluatorKind.GRADED
            and threshold is not None
            and r.verdict is Verdict.FAIL
        ):
            return Verdict.FAIL
    return Verdict.PASS


def run(
    tasklist: TaskList,
    evaluators: list[Evaluator],
    config,
) -> RunSummary:
    """Run every *evaluator* against *tasklist* and return an aggregated summary.

    Postconditions:
    - ``len(summary.results) == len(evaluators)``
    - ``summary.duration_ms >= 0``
    """
    threshold = getattr(config, "graded_threshold", None)
    tasklist_path = getattr(config, "tasklist_path", "")

    results: list[EvaluationResult] = []
    wall_start = time.perf_counter()

    for evaluator in evaluators:
        try:
            result = evaluator.evaluate(tasklist, config)
            result = _apply_threshold(result, threshold)
        except Exception as exc:  # noqa: BLE001 — isolate a faulty evaluator
            result = EvaluationResult(
                evaluator_id=getattr(evaluator, "id", "unknown"),
                kind=getattr(evaluator, "kind", EvaluatorKind.BINARY),
                verdict=Verdict.FAIL,
                score=None,
                summary=f"Evaluator raised an exception: {exc}",
                evidence=[f"Error: {type(exc).__name__}: {exc}"],
                details={"error": str(exc)},
            )
        results.append(result)

    duration_ms = int((time.perf_counter() - wall_start) * 1000)
    overall = _compute_overall(results, threshold)

    return RunSummary(
        tasklist_path=tasklist_path,
        results=results,
        overall_verdict=overall,
        duration_ms=duration_ms,
    )
