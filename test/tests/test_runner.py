"""Unit tests for test/harness/runner.py.

All tests mock check_activation so no real LLM calls are made.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from harness.exceptions import CheckerError
from harness.models import (
    ActivationResult,
    CheckResult,
    ExpectedOutcome,
    HarnessConfig,
    PromptCase,
    RunSummary,
    SkillDefinition,
)
from harness.runner import run

# --------------------------------------------------------------------------- #
# Shared test helpers / fixtures                                                #
# --------------------------------------------------------------------------- #

SKILL = SkillDefinition(
    name="test-skill",
    description="A test skill.",
    when_to_use="Use in tests.",
    raw_content="---\ndescription: A test skill.\n---\n## When to Use\nUse in tests.",
)

CONFIG = HarnessConfig(
    skill_path="/fake/SKILL.md",
    fixture_path="/fake/fixture.yaml",
    model="test-model",
    timeout_seconds=30,
    verbose=False,
)


def _make_case(case_id: str, expected: ExpectedOutcome = ExpectedOutcome.ACTIVATE) -> PromptCase:
    return PromptCase(id=case_id, prompt=f"Prompt for {case_id}", expected=expected)


def _make_result(case: PromptCase, passed: bool) -> CheckResult:
    actual = (
        ActivationResult.ACTIVATE if case.expected == ExpectedOutcome.ACTIVATE and passed
        else ActivationResult.NO_ACTIVATE if case.expected == ExpectedOutcome.NO_ACTIVATE and passed
        else ActivationResult.NO_ACTIVATE if case.expected == ExpectedOutcome.ACTIVATE
        else ActivationResult.ACTIVATE
    )
    return CheckResult(
        prompt_id=case.id,
        prompt=case.prompt,
        expected=case.expected,
        actual=actual,
        passed=passed,
        reasoning="Test reasoning.",
        latency_ms=10,
    )


# --------------------------------------------------------------------------- #
# Summary arithmetic invariants (Requirements 5.3, 5.4)                        #
# --------------------------------------------------------------------------- #

class TestRunSummaryArithmetic:
    def test_total_equals_number_of_cases(self):
        cases = [_make_case(f"case-{i}") for i in range(5)]
        results = [_make_result(c, True) for c in cases]
        with patch("harness.runner.check_activation", side_effect=results):
            summary = run(cases, SKILL, CONFIG)
        assert summary.total == 5

    def test_passed_plus_failed_plus_errors_equals_total(self):
        cases = [_make_case(f"case-{i}") for i in range(6)]
        # 2 pass, 2 fail, 2 error
        side_effects = (
            [_make_result(cases[0], True), _make_result(cases[1], True)]
            + [_make_result(cases[2], False), _make_result(cases[3], False)]
            + [CheckerError("boom"), CheckerError("boom")]
        )
        with patch("harness.runner.check_activation", side_effect=side_effects):
            summary = run(cases, SKILL, CONFIG)
        assert summary.passed + summary.failed + summary.errors == summary.total

    def test_all_passed(self):
        cases = [_make_case(f"case-{i}") for i in range(4)]
        results = [_make_result(c, True) for c in cases]
        with patch("harness.runner.check_activation", side_effect=results):
            summary = run(cases, SKILL, CONFIG)
        assert summary.passed == 4
        assert summary.failed == 0
        assert summary.errors == 0

    def test_all_failed(self):
        cases = [_make_case(f"case-{i}") for i in range(3)]
        results = [_make_result(c, False) for c in cases]
        with patch("harness.runner.check_activation", side_effect=results):
            summary = run(cases, SKILL, CONFIG)
        assert summary.passed == 0
        assert summary.failed == 3
        assert summary.errors == 0

    def test_all_errors(self):
        cases = [_make_case(f"case-{i}") for i in range(3)]
        with patch("harness.runner.check_activation", side_effect=CheckerError("api down")):
            summary = run(cases, SKILL, CONFIG)
        assert summary.passed == 0
        assert summary.failed == 0
        assert summary.errors == 3

    def test_mixed_pass_fail_error_counts(self):
        cases = [_make_case(f"case-{i}") for i in range(5)]
        side_effects = [
            _make_result(cases[0], True),
            _make_result(cases[1], False),
            CheckerError("timeout"),
            _make_result(cases[3], True),
            _make_result(cases[4], False),
        ]
        with patch("harness.runner.check_activation", side_effect=side_effects):
            summary = run(cases, SKILL, CONFIG)
        assert summary.passed == 2
        assert summary.failed == 2
        assert summary.errors == 1
        assert summary.total == 5

    def test_empty_cases_returns_zero_counts(self):
        with patch("harness.runner.check_activation") as mock_checker:
            summary = run([], SKILL, CONFIG)
        mock_checker.assert_not_called()
        assert summary.total == 0
        assert summary.passed == 0
        assert summary.failed == 0
        assert summary.errors == 0


# --------------------------------------------------------------------------- #
# Error isolation (Requirement 5.2)                                             #
# --------------------------------------------------------------------------- #

class TestErrorIsolation:
    def test_checker_error_does_not_abort_subsequent_cases(self):
        """A CheckerError on case N must not prevent case N+1 from being processed."""
        cases = [_make_case("ok-before"), _make_case("erroring"), _make_case("ok-after")]
        side_effects = [
            _make_result(cases[0], True),
            CheckerError("LLM unavailable"),
            _make_result(cases[2], True),
        ]
        with patch("harness.runner.check_activation", side_effect=side_effects):
            summary = run(cases, SKILL, CONFIG)
        assert len(summary.results) == 3
        assert summary.errors == 1
        assert summary.passed == 2

    def test_all_cases_appear_in_results_despite_errors(self):
        cases = [_make_case(f"c{i}") for i in range(4)]
        side_effects = [
            CheckerError("boom"),
            _make_result(cases[1], True),
            CheckerError("boom"),
            _make_result(cases[3], False),
        ]
        with patch("harness.runner.check_activation", side_effect=side_effects):
            summary = run(cases, SKILL, CONFIG)
        result_ids = [r.prompt_id for r in summary.results]
        assert result_ids == ["c0", "c1", "c2", "c3"]

    def test_error_result_has_correct_fields(self):
        """An errored CheckResult must have actual=None, passed=False, and error set."""
        case = _make_case("errored-case")
        with patch("harness.runner.check_activation", side_effect=CheckerError("api error")):
            summary = run([case], SKILL, CONFIG)
        result = summary.results[0]
        assert result.actual is None
        assert result.passed is False
        assert result.error is not None
        assert "api error" in result.error

    def test_error_result_preserves_prompt_id(self):
        case = _make_case("my-case-id")
        with patch("harness.runner.check_activation", side_effect=CheckerError("fail")):
            summary = run([case], SKILL, CONFIG)
        assert summary.results[0].prompt_id == "my-case-id"

    def test_error_result_preserves_expected(self):
        case = _make_case("case-x", ExpectedOutcome.NO_ACTIVATE)
        with patch("harness.runner.check_activation", side_effect=CheckerError("fail")):
            summary = run([case], SKILL, CONFIG)
        assert summary.results[0].expected == ExpectedOutcome.NO_ACTIVATE


# --------------------------------------------------------------------------- #
# Sequential processing and call arguments (Requirement 5.1)                   #
# --------------------------------------------------------------------------- #

class TestSequentialProcessing:
    def test_check_activation_called_once_per_case(self):
        cases = [_make_case(f"case-{i}") for i in range(4)]
        results = [_make_result(c, True) for c in cases]
        with patch("harness.runner.check_activation", side_effect=results) as mock_checker:
            run(cases, SKILL, CONFIG)
        assert mock_checker.call_count == 4

    def test_check_activation_called_with_correct_model(self):
        case = _make_case("single")
        result = _make_result(case, True)
        with patch("harness.runner.check_activation", return_value=result) as mock_checker:
            run([case], SKILL, CONFIG)
        _, kwargs = mock_checker.call_args
        assert kwargs["model"] == CONFIG.model

    def test_check_activation_called_with_correct_timeout(self):
        case = _make_case("single")
        result = _make_result(case, True)
        config = HarnessConfig(
            skill_path="/fake/SKILL.md",
            fixture_path="/fake/fixture.yaml",
            model="test-model",
            timeout_seconds=60,
        )
        with patch("harness.runner.check_activation", return_value=result) as mock_checker:
            run([case], SKILL, config)
        _, kwargs = mock_checker.call_args
        assert kwargs["timeout_seconds"] == 60

    def test_check_activation_called_with_correct_case(self):
        case = _make_case("specific-case")
        result = _make_result(case, True)
        with patch("harness.runner.check_activation", return_value=result) as mock_checker:
            run([case], SKILL, CONFIG)
        _, kwargs = mock_checker.call_args
        assert kwargs["prompt_case"] is case

    def test_check_activation_called_with_correct_skill(self):
        case = _make_case("single")
        result = _make_result(case, True)
        with patch("harness.runner.check_activation", return_value=result) as mock_checker:
            run([case], SKILL, CONFIG)
        _, kwargs = mock_checker.call_args
        assert kwargs["skill"] is SKILL


# --------------------------------------------------------------------------- #
# Duration (Requirement 5.5)                                                    #
# --------------------------------------------------------------------------- #

class TestDuration:
    def test_duration_ms_is_non_negative(self):
        cases = [_make_case("c0")]
        results = [_make_result(cases[0], True)]
        with patch("harness.runner.check_activation", side_effect=results):
            summary = run(cases, SKILL, CONFIG)
        assert summary.duration_ms >= 0

    def test_duration_ms_is_integer(self):
        cases = [_make_case("c0")]
        results = [_make_result(cases[0], True)]
        with patch("harness.runner.check_activation", side_effect=results):
            summary = run(cases, SKILL, CONFIG)
        assert isinstance(summary.duration_ms, int)
