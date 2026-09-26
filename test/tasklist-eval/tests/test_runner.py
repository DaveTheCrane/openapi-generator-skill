"""Tests for the runner's overall-verdict logic and evaluator isolation."""

from __future__ import annotations

from dataclasses import dataclass

from tasklist_eval.evaluators.base import Evaluator
from tasklist_eval.models import (
    EvaluationResult,
    EvaluatorKind,
    TaskList,
    Verdict,
)
from tasklist_eval.runner import run


@dataclass
class _Cfg:
    graded_threshold = None
    tasklist_path = "dummy.md"


class _StubBinary(Evaluator):
    id = "stub-binary"
    kind = EvaluatorKind.BINARY

    def __init__(self, verdict):
        self._verdict = verdict

    def evaluate(self, tasklist, config):
        return EvaluationResult(
            evaluator_id=self.id,
            kind=self.kind,
            verdict=self._verdict,
            score=None,
            summary="stub",
        )


class _StubGraded(Evaluator):
    id = "stub-graded"
    kind = EvaluatorKind.GRADED

    def __init__(self, score):
        self._score = score

    def evaluate(self, tasklist, config):
        verdict = Verdict.PASS if self._score >= 0.999 else (
            Verdict.PARTIAL if self._score > 0 else Verdict.FAIL
        )
        return EvaluationResult(
            evaluator_id=self.id,
            kind=self.kind,
            verdict=verdict,
            score=self._score,
            summary="stub graded",
        )


class _Exploding(Evaluator):
    id = "exploding"
    kind = EvaluatorKind.BINARY

    def evaluate(self, tasklist, config):
        raise RuntimeError("boom")


TL = TaskList(title="t")


def test_binary_pass_overall_pass():
    summary = run(TL, [_StubBinary(Verdict.PASS)], _Cfg())
    assert summary.overall_verdict is Verdict.PASS


def test_binary_fail_gates_overall():
    summary = run(TL, [_StubBinary(Verdict.PASS), _StubBinary(Verdict.FAIL)], _Cfg())
    assert summary.overall_verdict is Verdict.FAIL


def test_graded_informational_by_default():
    # A graded FAIL (score 0) does NOT gate overall when no threshold set.
    summary = run(TL, [_StubBinary(Verdict.PASS), _StubGraded(0.0)], _Cfg())
    assert summary.overall_verdict is Verdict.PASS


def test_graded_threshold_gates_when_below():
    cfg = _Cfg()
    cfg.graded_threshold = 0.5
    summary = run(TL, [_StubBinary(Verdict.PASS), _StubGraded(0.33)], cfg)
    assert summary.overall_verdict is Verdict.FAIL
    graded = next(r for r in summary.results if r.evaluator_id == "stub-graded")
    assert graded.verdict is Verdict.FAIL


def test_graded_threshold_pass_when_above():
    cfg = _Cfg()
    cfg.graded_threshold = 0.5
    summary = run(TL, [_StubBinary(Verdict.PASS), _StubGraded(0.75)], cfg)
    assert summary.overall_verdict is Verdict.PASS


def test_exploding_evaluator_isolated():
    summary = run(TL, [_StubBinary(Verdict.PASS), _Exploding()], _Cfg())
    # Whole run does not abort; error becomes a FAIL result.
    assert len(summary.results) == 2
    err = next(r for r in summary.results if r.evaluator_id == "exploding")
    assert err.verdict is Verdict.FAIL
    assert "exception" in err.summary.lower()
    # A binary FAIL gates the overall verdict.
    assert summary.overall_verdict is Verdict.FAIL


def test_duration_non_negative():
    summary = run(TL, [_StubBinary(Verdict.PASS)], _Cfg())
    assert summary.duration_ms >= 0
    assert summary.tasklist_path == "dummy.md"
