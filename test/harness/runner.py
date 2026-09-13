"""Test runner — orchestrates activation checks over all prompt cases."""

from __future__ import annotations

import time

from harness.activation_checker import check_activation
from harness.exceptions import CheckerError
from harness.models import (
    CheckResult,
    HarnessConfig,
    PromptCase,
    RunSummary,
    SkillDefinition,
)


def run(
    cases: list[PromptCase],
    skill: SkillDefinition,
    config: HarnessConfig,
) -> RunSummary:
    """Run activation checks for every *case* and return an aggregated summary.

    Each case is checked sequentially (no parallelism) to avoid rate-limit
    errors.  A :class:`~harness.exceptions.CheckerError` raised for any
    individual case is caught, recorded as an error, and does *not* abort the
    remaining cases.

    Postconditions:
    - ``summary.total == len(cases)``
    - ``summary.passed + summary.failed + summary.errors == summary.total``
    - ``summary.duration_ms >= 0``
    """
    results: list[CheckResult] = []
    passed = 0
    failed = 0
    errors = 0

    wall_start = time.perf_counter()

    for case in cases:
        try:
            result = check_activation(
                prompt_case=case,
                skill=skill,
                model=config.model,
                timeout_seconds=config.timeout_seconds,
                api_base=config.api_base,
                extra_params=config.extra_params,
            )
            if result.passed:
                passed += 1
            else:
                failed += 1
        except CheckerError as exc:
            result = CheckResult(
                prompt_id=case.id,
                prompt=case.prompt,
                expected=case.expected,
                actual=None,
                passed=False,
                reasoning="",
                latency_ms=0,
                error=str(exc),
            )
            errors += 1

        results.append(result)

    duration_ms = int((time.perf_counter() - wall_start) * 1000)

    return RunSummary(
        total=len(cases),
        passed=passed,
        failed=failed,
        errors=errors,
        results=results,
        duration_ms=duration_ms,
    )
