"""Unit tests for test/harness/reporter.py.

All tests capture stdout via pytest's capsys fixture and inspect the printed
output.  No LLM calls are made; all RunSummary objects are constructed
directly.
"""

from __future__ import annotations

import pytest

from harness.models import (
    ActivationResult,
    CheckResult,
    ExpectedOutcome,
    RunSummary,
)
from harness.reporter import report

# --------------------------------------------------------------------------- #
# Shared helpers                                                                #
# --------------------------------------------------------------------------- #


def _passed_result(case_id: str = "case-pass") -> CheckResult:
    return CheckResult(
        prompt_id=case_id,
        prompt="some prompt",
        expected=ExpectedOutcome.ACTIVATE,
        actual=ActivationResult.ACTIVATE,
        passed=True,
        reasoning="Looks like a match.",
        latency_ms=100,
    )


def _failed_result(case_id: str = "case-fail") -> CheckResult:
    return CheckResult(
        prompt_id=case_id,
        prompt="some prompt",
        expected=ExpectedOutcome.ACTIVATE,
        actual=ActivationResult.NO_ACTIVATE,
        passed=False,
        reasoning="Does not match.",
        latency_ms=150,
    )


def _error_result(case_id: str = "case-error", error: str = "timeout") -> CheckResult:
    return CheckResult(
        prompt_id=case_id,
        prompt="some prompt",
        expected=ExpectedOutcome.NO_ACTIVATE,
        actual=None,
        passed=False,
        reasoning="",
        latency_ms=0,
        error=error,
    )


def _make_summary(*results: CheckResult) -> RunSummary:
    passed = sum(1 for r in results if r.passed and r.error is None)
    errors = sum(1 for r in results if r.error is not None)
    failed = len(results) - passed - errors
    return RunSummary(
        total=len(results),
        passed=passed,
        failed=failed,
        errors=errors,
        results=list(results),
        duration_ms=500,
    )


# --------------------------------------------------------------------------- #
# Visual markers                                                                #
# --------------------------------------------------------------------------- #


class TestVisualMarkers:
    def test_passed_case_shows_checkmark(self, capsys):
        summary = _make_summary(_passed_result())
        report(summary, verbose=False)
        out = capsys.readouterr().out
        assert "✓" in out

    def test_failed_case_shows_cross(self, capsys):
        summary = _make_summary(_failed_result())
        report(summary, verbose=False)
        out = capsys.readouterr().out
        assert "✗" in out

    def test_error_case_shows_exclamation(self, capsys):
        summary = _make_summary(_error_result())
        report(summary, verbose=False)
        out = capsys.readouterr().out
        assert "!" in out

    def test_passed_case_does_not_show_fail_label(self, capsys):
        summary = _make_summary(_passed_result())
        report(summary, verbose=False)
        out = capsys.readouterr().out
        assert "FAIL" not in out

    def test_failed_case_shows_fail_label(self, capsys):
        summary = _make_summary(_failed_result())
        report(summary, verbose=False)
        out = capsys.readouterr().out
        assert "FAIL" in out


# --------------------------------------------------------------------------- #
# Result line content                                                           #
# --------------------------------------------------------------------------- #


class TestResultLineContent:
    def test_result_line_contains_case_id(self, capsys):
        summary = _make_summary(_passed_result("my-unique-id"))
        report(summary, verbose=False)
        out = capsys.readouterr().out
        assert "my-unique-id" in out

    def test_result_line_shows_expected_value(self, capsys):
        summary = _make_summary(_passed_result())
        report(summary, verbose=False)
        out = capsys.readouterr().out
        assert "activate" in out

    def test_result_line_shows_actual_value_for_passed(self, capsys):
        result = _passed_result()
        summary = _make_summary(result)
        report(summary, verbose=False)
        out = capsys.readouterr().out
        # Both expected and actual are "activate"
        assert "activate → activate" in out

    def test_result_line_shows_actual_value_for_failed(self, capsys):
        result = _failed_result()
        summary = _make_summary(result)
        report(summary, verbose=False)
        out = capsys.readouterr().out
        assert "activate → no_activate" in out

    def test_error_result_line_shows_error_message(self, capsys):
        result = _error_result(error="connection refused")
        summary = _make_summary(result)
        report(summary, verbose=False)
        out = capsys.readouterr().out
        assert "connection refused" in out
        assert "ERROR" in out

    def test_output_starts_with_header(self, capsys):
        summary = _make_summary(_passed_result())
        report(summary, verbose=False)
        out = capsys.readouterr().out
        assert out.startswith("Running skill activation tests...")

    def test_all_case_ids_appear_in_output(self, capsys):
        results = [
            _passed_result("alpha"),
            _failed_result("beta"),
            _error_result("gamma"),
        ]
        summary = _make_summary(*results)
        report(summary, verbose=False)
        out = capsys.readouterr().out
        assert "alpha" in out
        assert "beta" in out
        assert "gamma" in out


# --------------------------------------------------------------------------- #
# Summary line                                                                  #
# --------------------------------------------------------------------------- #


class TestSummaryLine:
    def test_summary_shows_passed_count(self, capsys):
        summary = _make_summary(_passed_result(), _passed_result("p2"))
        report(summary, verbose=False)
        out = capsys.readouterr().out
        assert "2 passed" in out

    def test_summary_shows_failed_count(self, capsys):
        summary = _make_summary(_failed_result(), _failed_result("f2"))
        report(summary, verbose=False)
        out = capsys.readouterr().out
        assert "2 failed" in out

    def test_summary_shows_error_count(self, capsys):
        summary = _make_summary(_error_result())
        report(summary, verbose=False)
        out = capsys.readouterr().out
        assert "1 error" in out

    def test_summary_shows_total_count(self, capsys):
        summary = _make_summary(_passed_result(), _failed_result(), _error_result())
        report(summary, verbose=False)
        out = capsys.readouterr().out
        assert "3 total" in out

    def test_summary_line_contains_results_label(self, capsys):
        summary = _make_summary(_passed_result())
        report(summary, verbose=False)
        out = capsys.readouterr().out
        assert "Results:" in out


# --------------------------------------------------------------------------- #
# Verbose mode                                                                  #
# --------------------------------------------------------------------------- #


class TestVerboseMode:
    def test_verbose_includes_reasoning(self, capsys):
        result = _passed_result()
        result.reasoning = "Very specific reasoning text."
        summary = _make_summary(result)
        report(summary, verbose=True)
        out = capsys.readouterr().out
        assert "Very specific reasoning text." in out

    def test_non_verbose_excludes_reasoning(self, capsys):
        result = _passed_result()
        result.reasoning = "Secret reasoning content."
        summary = _make_summary(result)
        report(summary, verbose=False)
        out = capsys.readouterr().out
        assert "Secret reasoning content." not in out

    def test_verbose_includes_reasoning_for_all_cases(self, capsys):
        r1 = _passed_result("c1")
        r1.reasoning = "Reason one."
        r2 = _failed_result("c2")
        r2.reasoning = "Reason two."
        summary = _make_summary(r1, r2)
        report(summary, verbose=True)
        out = capsys.readouterr().out
        assert "Reason one." in out
        assert "Reason two." in out

    def test_verbose_empty_reasoning_does_not_crash(self, capsys):
        result = _error_result()  # error results have empty reasoning
        summary = _make_summary(result)
        # Should not raise
        report(summary, verbose=True)

    def test_verbose_reasoning_appears_after_result_line(self, capsys):
        result = _passed_result("my-case")
        result.reasoning = "my reasoning here"
        summary = _make_summary(result)
        report(summary, verbose=True)
        out = capsys.readouterr().out
        id_pos = out.index("my-case")
        reasoning_pos = out.index("my reasoning here")
        assert reasoning_pos > id_pos


# --------------------------------------------------------------------------- #
# Exit code                                                                     #
# --------------------------------------------------------------------------- #


class TestExitCode:
    def test_all_passed_returns_zero(self, capsys):
        summary = _make_summary(_passed_result(), _passed_result("p2"))
        code = report(summary, verbose=False)
        assert code == 0

    def test_one_failure_returns_one(self, capsys):
        summary = _make_summary(_passed_result(), _failed_result())
        code = report(summary, verbose=False)
        assert code == 1

    def test_one_error_returns_one(self, capsys):
        summary = _make_summary(_passed_result(), _error_result())
        code = report(summary, verbose=False)
        assert code == 1

    def test_all_failed_returns_one(self, capsys):
        summary = _make_summary(_failed_result(), _failed_result("f2"))
        code = report(summary, verbose=False)
        assert code == 1

    def test_all_errors_returns_one(self, capsys):
        summary = _make_summary(_error_result(), _error_result("e2"))
        code = report(summary, verbose=False)
        assert code == 1

    def test_empty_summary_returns_zero(self, capsys):
        summary = RunSummary(total=0, passed=0, failed=0, errors=0, results=[], duration_ms=0)
        code = report(summary, verbose=False)
        assert code == 0
