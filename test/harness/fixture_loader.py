"""Fixture loader for the skill test harness.

Parses a YAML fixture file and returns a validated list of PromptCase objects.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from harness.exceptions import FixtureLoadError
from harness.models import ExpectedOutcome, PromptCase

# Pattern for valid case IDs.
_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

# Set of valid expected values (raw strings from YAML).
_VALID_EXPECTED = {"activate", "no_activate"}


def load_fixture(path: str) -> list[PromptCase]:
    """Parse a YAML fixture file and return a validated list of PromptCase objects.

    Args:
        path: Filesystem path to the fixture YAML file.

    Returns:
        A non-empty list of PromptCase objects, one per validated case entry.

    Raises:
        FixtureLoadError: If the file cannot be read, is not valid YAML, or fails
            any schema or uniqueness constraint.
    """
    file_path = Path(path)

    # --- Read and parse -------------------------------------------------------
    try:
        raw = file_path.read_text(encoding="utf-8")
    except OSError as exc:
        raise FixtureLoadError(f"Cannot read fixture file '{path}': {exc}") from exc

    try:
        data: Any = yaml.safe_load(raw)
    except yaml.YAMLError as exc:
        raise FixtureLoadError(
            f"Fixture file '{path}' is not valid YAML: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise FixtureLoadError(
            f"Fixture file '{path}' must be a YAML mapping at the top level."
        )

    # --- Validate top-level structure -----------------------------------------
    raw_cases = data.get("cases")
    if not raw_cases:
        raise FixtureLoadError(
            f"Fixture file '{path}' must contain a non-empty 'cases' list."
        )
    if not isinstance(raw_cases, list):
        raise FixtureLoadError(
            f"Fixture file '{path}': 'cases' must be a list, got {type(raw_cases).__name__}."
        )

    # --- Validate and build PromptCase objects ---------------------------------
    cases: list[PromptCase] = []
    seen_ids: dict[str, int] = {}  # id -> first-seen index (0-based)

    for idx, raw_case in enumerate(raw_cases):
        if not isinstance(raw_case, dict):
            raise FixtureLoadError(
                f"Fixture file '{path}': case at index {idx} must be a mapping, "
                f"got {type(raw_case).__name__}."
            )

        case_id = _validate_id(raw_case, idx, path)
        prompt = _validate_prompt(raw_case, idx, path)
        expected = _validate_expected(raw_case, idx, path)
        notes: str | None = raw_case.get("notes")
        if notes is not None and not isinstance(notes, str):
            notes = str(notes)

        # Uniqueness check
        if case_id in seen_ids:
            raise FixtureLoadError(
                f"Fixture file '{path}': duplicate id '{case_id}' at index {idx} "
                f"(first seen at index {seen_ids[case_id]})."
            )
        seen_ids[case_id] = idx

        cases.append(PromptCase(id=case_id, prompt=prompt, expected=expected, notes=notes))

    return cases


# --------------------------------------------------------------------------- #
# Private helpers                                                               #
# --------------------------------------------------------------------------- #


def _validate_id(raw_case: dict[str, Any], idx: int, path: str) -> str:
    """Extract and validate the 'id' field from a raw case dict."""
    if "id" not in raw_case:
        raise FixtureLoadError(
            f"Fixture file '{path}': case at index {idx} is missing required field 'id'."
        )
    case_id = raw_case["id"]
    if not isinstance(case_id, str) or not case_id.strip():
        raise FixtureLoadError(
            f"Fixture file '{path}': case at index {idx} has an empty or non-string 'id'."
        )
    if not _ID_PATTERN.match(case_id):
        raise FixtureLoadError(
            f"Fixture file '{path}': case at index {idx} has invalid 'id' '{case_id}'. "
            "IDs must match ^[a-zA-Z0-9_-]+$."
        )
    return case_id


def _validate_prompt(raw_case: dict[str, Any], idx: int, path: str) -> str:
    """Extract and validate the 'prompt' field from a raw case dict."""
    if "prompt" not in raw_case:
        raise FixtureLoadError(
            f"Fixture file '{path}': case at index {idx} is missing required field 'prompt'."
        )
    prompt = raw_case["prompt"]
    if not isinstance(prompt, str) or not prompt.strip():
        raise FixtureLoadError(
            f"Fixture file '{path}': case at index {idx} has an empty or non-string 'prompt'."
        )
    return prompt


def _validate_expected(raw_case: dict[str, Any], idx: int, path: str) -> ExpectedOutcome:
    """Extract and validate the 'expected' field from a raw case dict."""
    if "expected" not in raw_case:
        raise FixtureLoadError(
            f"Fixture file '{path}': case at index {idx} is missing required field 'expected'."
        )
    expected_raw = raw_case["expected"]
    if expected_raw not in _VALID_EXPECTED:
        raise FixtureLoadError(
            f"Fixture file '{path}': case at index {idx} has invalid 'expected' value "
            f"'{expected_raw}'. Must be 'activate' or 'no_activate'."
        )
    return ExpectedOutcome(expected_raw)
