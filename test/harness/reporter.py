"""Result reporter — formats and prints run results, returns exit code."""

from __future__ import annotations

import sys

from harness.models import CheckResult, RunSummary

# Visual markers for each case outcome
_PASS_MARKER = "✓"
_FAIL_MARKER = "✗"
_ERR_MARKER = "!"

# Column width for the case ID field (left-aligned, padded)
_ID_WIDTH = 30


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


def report(summary: RunSummary, verbose: bool) -> int:
    """Print test results to stdout and return the appropriate exit code.

    Parameters
    ----------
    summary:
        Aggregated results from the test runner.
    verbose:
        When ``True``, print the LLM's reasoning below each result line.

    Returns
    -------
    int
        ``0`` if all cases passed (``failed == 0`` and ``errors == 0``),
        ``1`` otherwise.
    """
    print("Running skill activation tests...\n")

    for result in summary.results:
        print(_format_result_line(result))
        if verbose and result.reasoning:
            # Indent reasoning under the result line
            for reasoning_line in result.reasoning.splitlines():
                print(f"      {reasoning_line}")

    print()
    print(
        f"Results: {summary.passed} passed, {summary.failed} failed,"
        f" {summary.errors} error  ({summary.total} total)"
    )

    return 0 if summary.failed == 0 and summary.errors == 0 else 1
