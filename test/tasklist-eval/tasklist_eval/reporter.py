"""Result reporter — renders a run in text, JSON, or JUnit XML; returns exit code.

Three output formats are supported, selected via ``config.report_format``:

* ``text``  — human-readable console report with per-evaluator markers.
* ``json``  — a CI-agnostic JSON document.
* ``junit`` — a well-formed JUnit XML document.

The report is printed to stdout, or written to ``config.report_file`` (with a
short ``Report written to <path>`` confirmation on stdout) when that path is set.

Exit code is format-independent: ``0`` iff the overall verdict is PASS, else ``1``.

JUnit note: JUnit has no native "partial" state. A PARTIAL evaluator is emitted
as a PASSING ``<testcase>`` (no ``<failure>``), with its score and summary
recorded in ``<system-out>`` so the partial signal is not lost.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from .models import EvaluationResult, EvaluatorKind, RunSummary, Verdict

_PASS_MARKER = "✓"
_FAIL_MARKER = "✗"
_PARTIAL_MARKER = "~"

_TOOL_NAME = "tasklist-eval"


def _utc_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()


def _exit_code(summary: RunSummary) -> int:
    """Return 0 iff the overall verdict is PASS, else 1."""
    return 0 if summary.overall_verdict is Verdict.PASS else 1


def _marker(verdict: Verdict) -> str:
    if verdict is Verdict.PASS:
        return _PASS_MARKER
    if verdict is Verdict.PARTIAL:
        return _PARTIAL_MARKER
    return _FAIL_MARKER


# --------------------------------------------------------------------------- #
# Renderers                                                                     #
# --------------------------------------------------------------------------- #


def _render_text(summary: RunSummary, config) -> str:
    lines: list[str] = []
    lines.append(f"Evaluating tasklist: {summary.tasklist_path}\n")

    for r in summary.results:
        marker = _marker(r.verdict)
        header = f"  {marker} {r.evaluator_id}  [{r.kind.value}]  {r.verdict.value.upper()}"
        if r.kind is EvaluatorKind.GRADED and r.score is not None:
            header += f"  score: {r.score:.2f}"
        lines.append(header)
        lines.append(f"      {r.summary}")
        for bullet in r.evidence:
            lines.append(f"        - {bullet}")
        lines.append("")

    lines.append(f"Overall: {summary.overall_verdict.value.upper()}")

    lines.append("")
    lines.append(f"Tasklist: {summary.tasklist_path}")
    lines.append(f"Evaluators: {len(summary.results)}")
    lines.append(f"Duration: {summary.duration_ms} ms")
    lines.append(f"Timestamp: {_utc_timestamp()}")

    return "\n".join(lines) + "\n"


def _render_json(summary: RunSummary, config) -> str:
    document = {
        "tool": _TOOL_NAME,
        "metadata": {
            "tasklist": summary.tasklist_path,
            "timestamp": _utc_timestamp(),
            "duration_ms": summary.duration_ms,
        },
        "overall": summary.overall_verdict.value,
        "results": [
            {
                "evaluator_id": r.evaluator_id,
                "group": r.group or "",
                "kind": r.kind.value,
                "verdict": r.verdict.value,
                "score": r.score,
                "summary": r.summary,
                "evidence": r.evidence,
                "details": r.details,
            }
            for r in summary.results
        ],
    }
    return json.dumps(document, indent=2)


def _system_out_text(r: EvaluationResult) -> str:
    parts = [f"verdict: {r.verdict.value}"]
    if r.score is not None:
        parts.append(f"score: {r.score:.4f}")
    parts.append(f"summary: {r.summary}")
    for bullet in r.evidence:
        parts.append(f"evidence: {bullet}")
    return "\n".join(parts)


def _classname(r: EvaluationResult) -> str:
    """JUnit classname: ``tasklist-eval.<group>`` when grouped, else ``tasklist-eval``."""
    return f"{_TOOL_NAME}.{r.group}" if r.group else _TOOL_NAME


def _render_junit(summary: RunSummary, config) -> str:
    failures = sum(1 for r in summary.results if r.verdict is Verdict.FAIL)
    total = len(summary.results)

    testsuites = ET.Element("testsuites")
    testsuite = ET.SubElement(
        testsuites,
        "testsuite",
        {
            "name": _TOOL_NAME,
            "tests": str(total),
            "failures": str(failures),
            "errors": "0",
            "time": f"{summary.duration_ms / 1000:.3f}",
            "timestamp": _utc_timestamp(),
        },
    )

    properties = ET.SubElement(testsuite, "properties")
    ET.SubElement(
        properties,
        "property",
        {"name": "tasklist", "value": summary.tasklist_path},
    )
    ET.SubElement(
        properties,
        "property",
        {"name": "tool", "value": _TOOL_NAME},
    )

    for r in summary.results:
        testcase = ET.SubElement(
            testsuite,
            "testcase",
            {"name": r.evaluator_id, "classname": _classname(r)},
        )
        # PARTIAL is not a JUnit-native state → treated as passing; the score and
        # summary live in <system-out> below. Only FAIL emits a <failure>.
        if r.verdict is Verdict.FAIL:
            ET.SubElement(
                testcase,
                "failure",
                {"message": escape(r.summary), "type": r.kind.value},
            )
        system_out = ET.SubElement(testcase, "system-out")
        system_out.text = _system_out_text(r)

    body = ET.tostring(testsuites, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + body


_RENDERERS = {
    "text": _render_text,
    "json": _render_json,
    "junit": _render_junit,
}


def report(summary: RunSummary, config) -> int:
    """Render the run results and return the appropriate exit code.

    Returns
    -------
    int
        ``0`` if ``summary.overall_verdict`` is PASS, else ``1``. The exit code
        is independent of ``report_format``.
    """
    renderer = _RENDERERS.get(config.report_format, _render_text)
    rendered = renderer(summary, config)

    if config.report_file is None:
        print(rendered, end="" if config.report_format == "text" else "\n")
    else:
        with open(config.report_file, "w", encoding="utf-8") as fh:
            fh.write(rendered)
        print(f"Report written to {config.report_file}")

    return _exit_code(summary)
