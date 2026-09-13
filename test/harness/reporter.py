"""Result reporter — renders run results in multiple formats, returns exit code.

Three output formats are supported, selected via ``config.report_format``:

* ``text``  — the original human-readable console report (unchanged default).
* ``json``  — a pretty-printed, CI-agnostic JSON document.
* ``junit`` — a well-formed JUnit XML document.

The rendered report is printed to stdout, or written to ``config.report_file``
(with a short confirmation printed to stdout) when that path is set.

Exit-code semantics are format-independent: ``0`` iff there are no failures and
no errors, ``1`` otherwise.
"""

from __future__ import annotations

import json
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from xml.sax.saxutils import escape

from harness.models import CheckResult, HarnessConfig, RunSummary

# Visual markers for each case outcome
_PASS_MARKER = "✓"
_FAIL_MARKER = "✗"
_ERR_MARKER = "!"

# Column width for the case ID field (left-aligned, padded)
_ID_WIDTH = 30

_TOOL_NAME = "skill-activation-harness"


def _utc_timestamp() -> str:
    """Return the current time as an ISO 8601 UTC timestamp."""
    return datetime.now(timezone.utc).isoformat()


def _exit_code(summary: RunSummary) -> int:
    """Return 0 iff no failures and no errors, else 1."""
    return 0 if summary.failed == 0 and summary.errors == 0 else 1


def _format_result_line(result: CheckResult) -> str:
    """Return the fixed-format result line for a single case.

    Format:
        ✓ <id padded>    [<expected> → <actual>]
        ✗ <id padded>    [<expected> → <actual>]   FAIL
        ! <id padded>    [<expected> → ERROR: <msg>]
    """
    expected_str = result.expected.value

    if result.error is not None:
        # Error case — actual is None; show the error message
        marker = _ERR_MARKER
        outcome_str = f"[{expected_str} → ERROR: {result.error}]"
        suffix = ""
    elif result.passed:
        marker = _PASS_MARKER
        actual_str = result.actual.value  # type: ignore[union-attr]
        outcome_str = f"[{expected_str} → {actual_str}]"
        suffix = ""
    else:
        marker = _FAIL_MARKER
        actual_str = result.actual.value  # type: ignore[union-attr]
        outcome_str = f"[{expected_str} → {actual_str}]"
        suffix = "   FAIL"

    padded_id = result.prompt_id.ljust(_ID_WIDTH)
    return f"  {marker} {padded_id} {outcome_str}{suffix}"


# --------------------------------------------------------------------------- #
# Renderers                                                                     #
# --------------------------------------------------------------------------- #


def _render_text(summary: RunSummary, config: HarnessConfig) -> str:
    """Render the human-readable console report.

    Preserves the original output exactly: the header, per-case markers, the
    verbose reasoning indentation, and the ``Results: ...`` summary line. A
    short metadata footer is appended *after* the summary line so existing
    assertions continue to hold.
    """
    lines: list[str] = []
    lines.append("Running skill activation tests...\n")

    for result in summary.results:
        lines.append(_format_result_line(result))
        if config.verbose and result.reasoning:
            for reasoning_line in result.reasoning.splitlines():
                lines.append(f"      {reasoning_line}")

    lines.append("")
    lines.append(
        f"Results: {summary.passed} passed, {summary.failed} failed,"
        f" {summary.errors} error  ({summary.total} total)"
    )

    # Metadata footer — appended after the summary line so the existing
    # asserted substrings are unaffected.
    api_base_display = config.api_base if config.api_base else "default"
    lines.append("")
    lines.append(f"Model: {config.model}")
    lines.append(f"Timeout: {config.timeout_seconds}s")
    lines.append(f"API base: {api_base_display}")
    lines.append(f"Duration: {summary.duration_ms} ms")
    lines.append(f"Timestamp: {_utc_timestamp()}")

    return "\n".join(lines) + "\n"


def _render_json(summary: RunSummary, config: HarnessConfig) -> str:
    """Render a pretty-printed, CI-agnostic JSON report."""
    document = {
        "tool": _TOOL_NAME,
        "metadata": {
            "model": config.model,
            "timeout_seconds": config.timeout_seconds,
            "api_base": config.api_base,
            "timestamp": _utc_timestamp(),
            "duration_ms": summary.duration_ms,
        },
        "summary": {
            "total": summary.total,
            "passed": summary.passed,
            "failed": summary.failed,
            "errors": summary.errors,
        },
        "results": [
            {
                "id": r.prompt_id,
                "prompt": r.prompt,
                "expected": r.expected.value,
                "actual": r.actual.value if r.actual is not None else None,
                "passed": r.passed,
                "reasoning": r.reasoning,
                "latency_ms": r.latency_ms,
                "error": r.error,
            }
            for r in summary.results
        ],
    }
    return json.dumps(document, indent=2)


def _render_junit(summary: RunSummary, config: HarnessConfig) -> str:
    """Render a well-formed JUnit XML report."""
    testsuites = ET.Element("testsuites")
    testsuite = ET.SubElement(
        testsuites,
        "testsuite",
        {
            "name": "skill-activation",
            "tests": str(summary.total),
            "failures": str(summary.failed),
            "errors": str(summary.errors),
            "time": f"{summary.duration_ms / 1000:.3f}",
            "timestamp": _utc_timestamp(),
        },
    )

    properties = ET.SubElement(testsuite, "properties")
    ET.SubElement(
        properties,
        "property",
        {"name": "model", "value": config.model},
    )
    ET.SubElement(
        properties,
        "property",
        {"name": "timeout_seconds", "value": str(config.timeout_seconds)},
    )
    if config.api_base is not None:
        ET.SubElement(
            properties,
            "property",
            {"name": "api_base", "value": config.api_base},
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
            {
                "name": r.prompt_id,
                "classname": "skill-activation",
                "time": f"{r.latency_ms / 1000:.3f}",
            },
        )
        if r.error is not None:
            ET.SubElement(
                testcase,
                "error",
                {"message": escape(r.error), "type": "CheckerError"},
            )
        elif not r.passed:
            actual_str = r.actual.value if r.actual is not None else "null"
            message = f"expected {r.expected.value} got {actual_str}"
            ET.SubElement(
                testcase,
                "failure",
                {"message": escape(message), "type": "assertion"},
            )
        if r.reasoning:
            system_out = ET.SubElement(testcase, "system-out")
            system_out.text = f"reasoning: {r.reasoning}"

    body = ET.tostring(testsuites, encoding="unicode")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + body


_RENDERERS = {
    "text": _render_text,
    "json": _render_json,
    "junit": _render_junit,
}


def report(summary: RunSummary, config: HarnessConfig) -> int:
    """Render the run results and return the appropriate exit code.

    Parameters
    ----------
    summary:
        Aggregated results from the test runner.
    config:
        Resolved harness configuration. Supplies the report format, optional
        output file, verbosity, and run metadata (model, timeout, api_base).

    Returns
    -------
    int
        ``0`` if all cases passed (``failed == 0`` and ``errors == 0``),
        ``1`` otherwise. The exit code does not depend on ``report_format``.
    """
    renderer = _RENDERERS.get(config.report_format, _render_text)
    rendered = renderer(summary, config)

    if config.report_file is None:
        # ``rendered`` already carries its own trailing newline where relevant;
        # avoid adding a second blank line for the text format.
        print(rendered, end="" if config.report_format == "text" else "\n")
    else:
        with open(config.report_file, "w", encoding="utf-8") as fh:
            fh.write(rendered)
        print(f"Report written to {config.report_file}")

    return _exit_code(summary)
