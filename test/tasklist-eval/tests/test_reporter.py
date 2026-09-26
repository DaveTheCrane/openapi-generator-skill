"""Tests for the reporter across text, JSON, and JUnit formats."""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import pytest

from tasklist_eval.models import (
    EvaluationResult,
    EvaluatorKind,
    RunSummary,
    Verdict,
)
from tasklist_eval.reporter import report


@dataclass
class _Cfg:
    report_format: str = "text"
    report_file = None


def _summary(overall=Verdict.PASS):
    return RunSummary(
        tasklist_path="samples/x.md",
        results=[
            EvaluationResult(
                evaluator_id="generator-in-pom",
                kind=EvaluatorKind.BINARY,
                verdict=Verdict.PASS,
                score=None,
                summary="pom has generator",
                evidence=["Task 2: matched 'openapi-generator'"],
                details={"pom_modified": True},
            ),
            EvaluationResult(
                evaluator_id="generated-code-usage",
                kind=EvaluatorKind.GRADED,
                verdict=Verdict.PARTIAL,
                score=0.5,
                summary="1/2 areas generated",
                evidence=["[server] generated", "[address-client] handcoded"],
                details={"areas": {"server": "generated"}, "score": 0.5},
            ),
        ],
        overall_verdict=overall,
        duration_ms=12,
    )


def test_text_markers_and_overall(capsys):
    code = report(_summary(Verdict.PASS), _Cfg(report_format="text"))
    out = capsys.readouterr().out
    assert "Evaluating tasklist: samples/x.md" in out
    assert "✓ generator-in-pom" in out
    assert "~ generated-code-usage" in out
    assert "score: 0.50" in out
    assert "Overall: PASS" in out
    assert code == 0


def test_text_exit_code_fail(capsys):
    code = report(_summary(Verdict.FAIL), _Cfg(report_format="text"))
    out = capsys.readouterr().out
    assert "Overall: FAIL" in out
    assert code == 1


def test_json_schema(capsys):
    report(_summary(Verdict.PASS), _Cfg(report_format="json"))
    out = capsys.readouterr().out
    doc = json.loads(out)
    assert doc["tool"] == "tasklist-eval"
    assert doc["overall"] == "pass"
    assert doc["metadata"]["tasklist"] == "samples/x.md"
    assert len(doc["results"]) == 2
    graded = doc["results"][1]
    assert graded["kind"] == "graded"
    assert graded["score"] == 0.5
    assert graded["verdict"] == "partial"
    assert "details" in graded and "evidence" in graded


def test_junit_wellformed_and_counts(capsys):
    report(_summary(Verdict.FAIL), _Cfg(report_format="junit"))
    out = capsys.readouterr().out
    root = ET.fromstring(out)  # raises if not well-formed
    suite = root.find("testsuite")
    assert suite.get("name") == "tasklist-eval"
    assert suite.get("tests") == "2"
    # No FAIL verdicts in this summary → 0 failures (PARTIAL is not a failure).
    assert suite.get("failures") == "0"
    assert suite.get("errors") == "0"


def test_junit_partial_in_system_out(capsys):
    report(_summary(Verdict.PASS), _Cfg(report_format="junit"))
    out = capsys.readouterr().out
    root = ET.fromstring(out)
    cases = root.find("testsuite").findall("testcase")
    graded_case = next(c for c in cases if c.get("name") == "generated-code-usage")
    # PARTIAL → passing testcase (no <failure>) but score in <system-out>.
    assert graded_case.find("failure") is None
    system_out = graded_case.find("system-out")
    assert "score: 0.5" in system_out.text


def test_junit_failure_element():
    summary = RunSummary(
        tasklist_path="x.md",
        results=[
            EvaluationResult(
                evaluator_id="generator-in-pom",
                kind=EvaluatorKind.BINARY,
                verdict=Verdict.FAIL,
                score=None,
                summary="no generator in pom",
                evidence=["nothing matched"],
            )
        ],
        overall_verdict=Verdict.FAIL,
        duration_ms=1,
    )
    from tasklist_eval.reporter import _render_junit

    out = _render_junit(summary, _Cfg(report_format="junit"))
    root = ET.fromstring(out)
    suite = root.find("testsuite")
    assert suite.get("failures") == "1"
    case = suite.find("testcase")
    failure = case.find("failure")
    assert failure is not None
    assert failure.get("type") == "binary"
    assert "no generator" in failure.get("message")


def test_report_file_routing_json(tmp_path, capsys):
    out_file = tmp_path / "eval.json"
    cfg = _Cfg(report_format="json")
    cfg.report_file = str(out_file)
    code = report(_summary(Verdict.PASS), cfg)
    stdout = capsys.readouterr().out
    assert f"Report written to {out_file}" in stdout
    doc = json.loads(out_file.read_text(encoding="utf-8"))
    assert doc["overall"] == "pass"
    assert code == 0


def test_report_file_routing_junit_parseable(tmp_path):
    out_file = tmp_path / "eval.xml"
    cfg = _Cfg(report_format="junit")
    cfg.report_file = str(out_file)
    report(_summary(Verdict.FAIL), cfg)
    tree = ET.parse(str(out_file))  # raises if malformed
    assert tree.getroot().tag == "testsuites"
