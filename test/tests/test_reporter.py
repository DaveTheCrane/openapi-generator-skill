"""Unit tests for test/harness/reporter.py.

All tests capture stdout via pytest's capsys fixture and inspect the printed
output.  No LLM calls are made; all RunSummary objects are constructed
directly.
"""

from __future__ import annotations

import pytest

import json
import xml.etree.ElementTree as ET

from harness.models import (
    ActivationResult,
    CheckResult,
    ExpectedOutcome,
    HarnessConfig,
    RunSummary,
)
from harness.reporter import report


def _config(
    *,
    verbose: bool = False,
    report_format: str = "text",
    report_file: str | None = None,
    model: str = "test-model",
    timeout_seconds: int = 30,
    api_base: str | None = None,
) -> HarnessConfig:
    """Build a minimal HarnessConfig for reporter tests."""
    return HarnessConfig(
        skill_path="skill.md",
        fixture_path="fixture.yaml",
        model=model,
        timeout_seconds=timeout_seconds,
        verbose=verbose,
        api_base=api_base,
        report_format=report_format,
        report_file=report_file,
    )

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
        report(summary, _config(verbose=False))
        out = capsys.readouterr().out
        assert "✓" in out

    def test_failed_case_shows_cross(self, capsys):
        summary = _make_summary(_failed_result())
        report(summary, _config(verbose=False))
        out = capsys.readouterr().out
        assert "✗" in out

    def test_error_case_shows_exclamation(self, capsys):
        summary = _make_summary(_error_result())
        report(summary, _config(verbose=False))
        out = capsys.readouterr().out
        assert "!" in out

    def test_passed_case_does_not_show_fail_label(self, capsys):
        summary = _make_summary(_passed_result())
        report(summary, _config(verbose=False))
        out = capsys.readouterr().out
        assert "FAIL" not in out

    def test_failed_case_shows_fail_label(self, capsys):
        summary = _make_summary(_failed_result())
        report(summary, _config(verbose=False))
        out = capsys.readouterr().out
        assert "FAIL" in out


# --------------------------------------------------------------------------- #
# Result line content                                                           #
# --------------------------------------------------------------------------- #


class TestResultLineContent:
    def test_result_line_contains_case_id(self, capsys):
        summary = _make_summary(_passed_result("my-unique-id"))
        report(summary, _config(verbose=False))
        out = capsys.readouterr().out
        assert "my-unique-id" in out

    def test_result_line_shows_expected_value(self, capsys):
        summary = _make_summary(_passed_result())
        report(summary, _config(verbose=False))
        out = capsys.readouterr().out
        assert "activate" in out

    def test_result_line_shows_actual_value_for_passed(self, capsys):
        result = _passed_result()
        summary = _make_summary(result)
        report(summary, _config(verbose=False))
        out = capsys.readouterr().out
        # Both expected and actual are "activate"
        assert "activate → activate" in out

    def test_result_line_shows_actual_value_for_failed(self, capsys):
        result = _failed_result()
        summary = _make_summary(result)
        report(summary, _config(verbose=False))
        out = capsys.readouterr().out
        assert "activate → no_activate" in out

    def test_error_result_line_shows_error_message(self, capsys):
        result = _error_result(error="connection refused")
        summary = _make_summary(result)
        report(summary, _config(verbose=False))
        out = capsys.readouterr().out
        assert "connection refused" in out
        assert "ERROR" in out

    def test_output_starts_with_header(self, capsys):
        summary = _make_summary(_passed_result())
        report(summary, _config(verbose=False))
        out = capsys.readouterr().out
        assert out.startswith("Running skill activation tests...")

    def test_all_case_ids_appear_in_output(self, capsys):
        results = [
            _passed_result("alpha"),
            _failed_result("beta"),
            _error_result("gamma"),
        ]
        summary = _make_summary(*results)
        report(summary, _config(verbose=False))
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
        report(summary, _config(verbose=False))
        out = capsys.readouterr().out
        assert "2 passed" in out

    def test_summary_shows_failed_count(self, capsys):
        summary = _make_summary(_failed_result(), _failed_result("f2"))
        report(summary, _config(verbose=False))
        out = capsys.readouterr().out
        assert "2 failed" in out

    def test_summary_shows_error_count(self, capsys):
        summary = _make_summary(_error_result())
        report(summary, _config(verbose=False))
        out = capsys.readouterr().out
        assert "1 error" in out

    def test_summary_shows_total_count(self, capsys):
        summary = _make_summary(_passed_result(), _failed_result(), _error_result())
        report(summary, _config(verbose=False))
        out = capsys.readouterr().out
        assert "3 total" in out

    def test_summary_line_contains_results_label(self, capsys):
        summary = _make_summary(_passed_result())
        report(summary, _config(verbose=False))
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
        report(summary, _config(verbose=True))
        out = capsys.readouterr().out
        assert "Very specific reasoning text." in out

    def test_non_verbose_excludes_reasoning(self, capsys):
        result = _passed_result()
        result.reasoning = "Secret reasoning content."
        summary = _make_summary(result)
        report(summary, _config(verbose=False))
        out = capsys.readouterr().out
        assert "Secret reasoning content." not in out

    def test_verbose_includes_reasoning_for_all_cases(self, capsys):
        r1 = _passed_result("c1")
        r1.reasoning = "Reason one."
        r2 = _failed_result("c2")
        r2.reasoning = "Reason two."
        summary = _make_summary(r1, r2)
        report(summary, _config(verbose=True))
        out = capsys.readouterr().out
        assert "Reason one." in out
        assert "Reason two." in out

    def test_verbose_empty_reasoning_does_not_crash(self, capsys):
        result = _error_result()  # error results have empty reasoning
        summary = _make_summary(result)
        # Should not raise
        report(summary, _config(verbose=True))

    def test_verbose_reasoning_appears_after_result_line(self, capsys):
        result = _passed_result("my-case")
        result.reasoning = "my reasoning here"
        summary = _make_summary(result)
        report(summary, _config(verbose=True))
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
        code = report(summary, _config(verbose=False))
        assert code == 0

    def test_one_failure_returns_one(self, capsys):
        summary = _make_summary(_passed_result(), _failed_result())
        code = report(summary, _config(verbose=False))
        assert code == 1

    def test_one_error_returns_one(self, capsys):
        summary = _make_summary(_passed_result(), _error_result())
        code = report(summary, _config(verbose=False))
        assert code == 1

    def test_all_failed_returns_one(self, capsys):
        summary = _make_summary(_failed_result(), _failed_result("f2"))
        code = report(summary, _config(verbose=False))
        assert code == 1

    def test_all_errors_returns_one(self, capsys):
        summary = _make_summary(_error_result(), _error_result("e2"))
        code = report(summary, _config(verbose=False))
        assert code == 1

    def test_empty_summary_returns_zero(self, capsys):
        summary = RunSummary(total=0, passed=0, failed=0, errors=0, results=[], duration_ms=0)
        code = report(summary, _config(verbose=False))
        assert code == 0


# --------------------------------------------------------------------------- #
# Text metadata footer                                                          #
# --------------------------------------------------------------------------- #


class TestTextMetadataFooter:
    def test_text_includes_model_after_summary(self, capsys):
        summary = _make_summary(_passed_result())
        report(summary, _config(model="my-model-x"))
        out = capsys.readouterr().out
        results_pos = out.index("Results:")
        model_pos = out.index("Model: my-model-x")
        # Metadata footer must appear after the summary line.
        assert model_pos > results_pos

    def test_text_shows_duration(self, capsys):
        summary = _make_summary(_passed_result())
        report(summary, _config())
        out = capsys.readouterr().out
        assert "Duration: 500 ms" in out

    def test_text_api_base_default_when_none(self, capsys):
        summary = _make_summary(_passed_result())
        report(summary, _config(api_base=None))
        out = capsys.readouterr().out
        assert "API base: default" in out


# --------------------------------------------------------------------------- #
# JSON format                                                                   #
# --------------------------------------------------------------------------- #


class TestJsonFormat:
    def test_json_is_valid_and_has_top_level_keys(self, capsys):
        summary = _make_summary(_passed_result())
        report(summary, _config(report_format="json"))
        out = capsys.readouterr().out
        doc = json.loads(out)
        assert doc["tool"] == "skill-activation-harness"
        assert set(doc.keys()) == {"tool", "metadata", "summary", "results"}

    def test_json_metadata_has_model(self, capsys):
        summary = _make_summary(_passed_result())
        report(summary, _config(report_format="json", model="json-model"))
        doc = json.loads(capsys.readouterr().out)
        assert doc["metadata"]["model"] == "json-model"
        assert "timestamp" in doc["metadata"]
        assert doc["metadata"]["duration_ms"] == 500

    def test_json_summary_counts(self, capsys):
        summary = _make_summary(_passed_result(), _failed_result(), _error_result())
        report(summary, _config(report_format="json"))
        doc = json.loads(capsys.readouterr().out)
        assert doc["summary"] == {"total": 3, "passed": 1, "failed": 1, "errors": 1}

    def test_json_result_fields_for_passed(self, capsys):
        summary = _make_summary(_passed_result("json-pass"))
        report(summary, _config(report_format="json"))
        doc = json.loads(capsys.readouterr().out)
        result = doc["results"][0]
        assert result["id"] == "json-pass"
        assert result["expected"] == "activate"
        assert result["actual"] == "activate"
        assert result["passed"] is True
        assert result["error"] is None
        assert result["latency_ms"] == 100

    def test_json_actual_null_on_error(self, capsys):
        summary = _make_summary(_error_result(error="boom"))
        report(summary, _config(report_format="json"))
        doc = json.loads(capsys.readouterr().out)
        result = doc["results"][0]
        assert result["actual"] is None
        assert result["error"] == "boom"

    def test_json_exit_code_unaffected_by_format(self, capsys):
        summary = _make_summary(_passed_result())
        assert report(summary, _config(report_format="json")) == 0
        capsys.readouterr()
        summary = _make_summary(_failed_result())
        assert report(summary, _config(report_format="json")) == 1


# --------------------------------------------------------------------------- #
# JUnit format                                                                  #
# --------------------------------------------------------------------------- #


class TestJunitFormat:
    def test_junit_is_well_formed_xml(self, capsys):
        summary = _make_summary(_passed_result())
        report(summary, _config(report_format="junit"))
        out = capsys.readouterr().out
        # Parses without raising -> well-formed.
        root = ET.fromstring(out)
        assert root.tag == "testsuites"

    def test_junit_testsuite_counts(self, capsys):
        summary = _make_summary(_passed_result(), _failed_result(), _error_result())
        report(summary, _config(report_format="junit"))
        root = ET.fromstring(capsys.readouterr().out)
        suite = root.find("testsuite")
        assert suite.get("tests") == "3"
        assert suite.get("failures") == "1"
        assert suite.get("errors") == "1"

    def test_junit_has_model_property(self, capsys):
        summary = _make_summary(_passed_result())
        report(summary, _config(report_format="junit", model="junit-model"))
        root = ET.fromstring(capsys.readouterr().out)
        props = root.find("testsuite/properties")
        model_prop = [p for p in props if p.get("name") == "model"]
        assert len(model_prop) == 1
        assert model_prop[0].get("value") == "junit-model"

    def test_junit_failure_element_for_failed_case(self, capsys):
        summary = _make_summary(_failed_result("fail-case"))
        report(summary, _config(report_format="junit"))
        root = ET.fromstring(capsys.readouterr().out)
        testcase = root.find(".//testcase[@name='fail-case']")
        failure = testcase.find("failure")
        assert failure is not None
        assert "expected activate got no_activate" in failure.get("message")

    def test_junit_error_element_for_error_case(self, capsys):
        summary = _make_summary(_error_result("err-case", error="connection lost"))
        report(summary, _config(report_format="junit"))
        root = ET.fromstring(capsys.readouterr().out)
        testcase = root.find(".//testcase[@name='err-case']")
        error = testcase.find("error")
        assert error is not None
        assert error.get("message") == "connection lost"

    def test_junit_reasoning_in_system_out(self, capsys):
        result = _passed_result("reason-case")
        result.reasoning = "the reasoning appears here"
        summary = _make_summary(result)
        report(summary, _config(report_format="junit"))
        root = ET.fromstring(capsys.readouterr().out)
        testcase = root.find(".//testcase[@name='reason-case']")
        system_out = testcase.find("system-out")
        assert system_out is not None
        assert "the reasoning appears here" in system_out.text

    def test_junit_exit_code_unaffected_by_format(self, capsys):
        summary = _make_summary(_error_result())
        assert report(summary, _config(report_format="junit")) == 1


# --------------------------------------------------------------------------- #
# report_file output routing                                                    #
# --------------------------------------------------------------------------- #


class TestReportFile:
    def test_json_written_to_file(self, tmp_path, capsys):
        out_file = tmp_path / "report.json"
        summary = _make_summary(_passed_result())
        code = report(
            summary,
            _config(report_format="json", report_file=str(out_file)),
        )
        assert code == 0
        assert out_file.exists()
        doc = json.loads(out_file.read_text(encoding="utf-8"))
        assert doc["tool"] == "skill-activation-harness"

    def test_confirmation_printed_to_stdout(self, tmp_path, capsys):
        out_file = tmp_path / "report.json"
        summary = _make_summary(_passed_result())
        report(summary, _config(report_format="json", report_file=str(out_file)))
        out = capsys.readouterr().out
        assert f"Report written to {out_file}" in out
        # The JSON body itself is not printed to stdout when writing to a file.
        assert "skill-activation-harness" not in out

    def test_junit_written_to_file_is_well_formed(self, tmp_path, capsys):
        out_file = tmp_path / "report.xml"
        summary = _make_summary(_failed_result())
        code = report(
            summary,
            _config(report_format="junit", report_file=str(out_file)),
        )
        assert code == 1
        assert out_file.exists()
        root = ET.fromstring(out_file.read_text(encoding="utf-8"))
        assert root.tag == "testsuites"

    def test_text_written_to_file(self, tmp_path, capsys):
        out_file = tmp_path / "report.txt"
        summary = _make_summary(_passed_result())
        code = report(
            summary,
            _config(report_format="text", report_file=str(out_file)),
        )
        assert code == 0
        content = out_file.read_text(encoding="utf-8")
        assert "Running skill activation tests..." in content
        assert "Results:" in content

    def test_file_write_does_not_change_exit_code(self, tmp_path, capsys):
        out_file = tmp_path / "report.json"
        summary = _make_summary(_error_result())
        code = report(
            summary,
            _config(report_format="json", report_file=str(out_file)),
        )
        assert code == 1
