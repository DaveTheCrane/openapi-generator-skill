"""YAML-based evaluator loader.

Parses a YAML file into one or more :class:`~tasklist_eval.evaluators.BinaryEvaluator`
or :class:`~tasklist_eval.evaluators.GradedEvaluator` instances.

YAML Schema
-----------
At the top level the file is a mapping with a required ``evaluators`` list.
An optional ``group`` key names the plugin group; when absent the group is
inferred from the containing folder name (same as for Python plugins).

.. code-block:: yaml

    group: my-skill          # optional; inferred from folder name if absent

    evaluators:
      - id: my-binary-check  # required, non-empty
        kind: binary          # "binary" or "graded"
        description: "..."    # optional
        # --- binary-only fields ---
        require:
          - name: pom-modified
            patterns:
              - 'pom\\.xml'
              - 'maven\\s+build'
            flags: IGNORECASE  # optional; IGNORECASE is the default
        forbid:
          - name: skip-signal
            patterns: ['skip the tests']
        summaries:             # optional
          pass: "All good."
          missing:pom-modified: "pom.xml not found."
          missing:all: "Nothing found."
          fail: "Generic fail."

      - id: my-graded-check
        kind: graded
        description: "..."
        # --- graded-only fields ---
        success_label: generated   # optional, default "success"
        failure_label: handcoded   # optional, default "failure"
        conflict_winner: success   # optional, default "success"
        unmatched_present: failure # optional, default "failure"
        pass_threshold: 0.999      # optional, default 0.999
        areas:
          - name: server
            presence:
              name: server-presence
              patterns: ['controller']
            success:
              - name: generated
                patterns: ['ApiDelegate']
            failure:
              - name: server-handcoded
                patterns: ['@RestController']

Pattern flags
~~~~~~~~~~~~~
The ``flags`` key on a pattern set accepts a comma-separated list of
``re`` flag names: ``IGNORECASE``, ``MULTILINE``, ``DOTALL``, ``VERBOSE``.
Defaults to ``IGNORECASE`` when omitted.

Errors
~~~~~~
:class:`~tasklist_eval.exceptions.PluginError` is raised for any schema
violation so the caller can emit a single, descriptive error message.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

import yaml

from .evaluators.base import Evaluator
from .evaluators.binary import BinaryEvaluator
from .evaluators.graded import Area, GradedEvaluator
from .evaluators.patterns import PatternSet
from .exceptions import PluginError

# Supported re flag names.
_FLAG_MAP: dict[str, int] = {
    "IGNORECASE": re.IGNORECASE,
    "I": re.IGNORECASE,
    "MULTILINE": re.MULTILINE,
    "M": re.MULTILINE,
    "DOTALL": re.DOTALL,
    "S": re.DOTALL,
    "VERBOSE": re.VERBOSE,
    "X": re.VERBOSE,
}

_VALID_KINDS = ("binary", "graded")
_VALID_CONFLICT = ("success", "failure")


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def load_yaml_evaluators(path: str | Path) -> list[Evaluator]:
    """Parse *path* and return a list of evaluator instances.

    Parameters
    ----------
    path:
        Filesystem path to the ``.yaml`` / ``.yml`` evaluator file.

    Returns
    -------
    list[Evaluator]
        One or more evaluator instances declared in the file.

    Raises
    ------
    PluginError
        On any I/O, YAML parse, or schema validation error.
    """
    path = Path(path).resolve()
    if not path.is_file():
        raise PluginError(f"YAML evaluator file does not exist: {str(path)!r}")

    try:
        raw_text = path.read_text(encoding="utf-8")
    except OSError as exc:
        raise PluginError(
            f"Cannot read YAML evaluator file {str(path)!r}: {exc}"
        ) from exc

    try:
        data: Any = yaml.safe_load(raw_text)
    except yaml.YAMLError as exc:
        raise PluginError(
            f"YAML evaluator file {str(path)!r} is not valid YAML: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: top-level must be a mapping."
        )

    # ``group`` is optional at the top level; the plugin loader fills it in
    # from the folder name when absent (same convention as Python plugins).
    file_group: str | None = None
    if "group" in data:
        raw_group = data["group"]
        if not isinstance(raw_group, str) or not raw_group.strip():
            raise PluginError(
                f"YAML evaluator file {str(path)!r}: 'group' must be a non-empty string."
            )
        file_group = raw_group.strip()

    raw_evaluators = data.get("evaluators")
    if raw_evaluators is None:
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: missing required 'evaluators' key."
        )
    if not isinstance(raw_evaluators, list) or not raw_evaluators:
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: 'evaluators' must be a non-empty list."
        )

    evaluators: list[Evaluator] = []
    for idx, raw_ev in enumerate(raw_evaluators):
        ev = _parse_evaluator(raw_ev, idx, path)
        if file_group and not ev.plugin_group:
            ev.plugin_group = file_group
        evaluators.append(ev)

    return evaluators


# ---------------------------------------------------------------------------
# Evaluator parsing
# ---------------------------------------------------------------------------


def _parse_evaluator(raw: Any, idx: int, path: Path) -> Evaluator:
    """Parse one evaluator mapping from the ``evaluators`` list."""
    _require_mapping(raw, f"evaluators[{idx}]", path)

    ev_id = _require_str(raw, "id", f"evaluators[{idx}]", path)
    if not ev_id.strip():
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: evaluators[{idx}].id must be non-empty."
        )
    ev_id = ev_id.strip()

    kind_raw = _require_str(raw, "kind", f"evaluators[{idx}] (id={ev_id!r})", path)
    if kind_raw not in _VALID_KINDS:
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: evaluators[{idx}] (id={ev_id!r}) "
            f"'kind' must be one of {_VALID_KINDS}, got {kind_raw!r}."
        )

    description: str = ""
    if "description" in raw:
        description = str(raw["description"])

    if kind_raw == "binary":
        return _parse_binary(raw, ev_id, description, path)
    else:
        return _parse_graded(raw, ev_id, description, path)


def _parse_binary(
    raw: dict, ev_id: str, description: str, path: Path
) -> BinaryEvaluator:
    """Build a :class:`BinaryEvaluator` from a raw mapping."""
    ctx = f"evaluators id={ev_id!r}"

    require_raw = raw.get("require", [])
    forbid_raw = raw.get("forbid", [])

    if not isinstance(require_raw, list):
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: {ctx} 'require' must be a list."
        )
    if not isinstance(forbid_raw, list):
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: {ctx} 'forbid' must be a list."
        )

    require = [
        _parse_pattern_set(ps, f"{ctx}.require[{i}]", path)
        for i, ps in enumerate(require_raw)
    ]
    forbid = [
        _parse_pattern_set(ps, f"{ctx}.forbid[{i}]", path)
        for i, ps in enumerate(forbid_raw)
    ]

    if not require and not forbid:
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: {ctx} binary evaluator needs "
            "at least one 'require' or 'forbid' pattern set."
        )

    summaries: dict[str, str] = {}
    if "summaries" in raw:
        raw_summaries = raw["summaries"]
        if not isinstance(raw_summaries, dict):
            raise PluginError(
                f"YAML evaluator file {str(path)!r}: {ctx} 'summaries' must be a mapping."
            )
        for key, value in raw_summaries.items():
            summaries[str(key)] = str(value)

    ev = BinaryEvaluator(
        id=ev_id,
        description=description,
        require=require,
        forbid=forbid or None,
        summaries=summaries or None,
    )
    return ev


def _parse_graded(
    raw: dict, ev_id: str, description: str, path: Path
) -> GradedEvaluator:
    """Build a :class:`GradedEvaluator` from a raw mapping."""
    ctx = f"evaluators id={ev_id!r}"

    areas_raw = raw.get("areas")
    if not isinstance(areas_raw, list) or not areas_raw:
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: {ctx} 'areas' must be a non-empty list."
        )

    areas = [
        _parse_area(ar, f"{ctx}.areas[{i}]", path)
        for i, ar in enumerate(areas_raw)
    ]

    success_label: str = str(raw.get("success_label", "success"))
    failure_label: str = str(raw.get("failure_label", "failure"))
    conflict_winner: str = str(raw.get("conflict_winner", "success"))
    unmatched_present: str = str(raw.get("unmatched_present", "failure"))

    if conflict_winner not in _VALID_CONFLICT:
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: {ctx} 'conflict_winner' must be "
            f"one of {_VALID_CONFLICT}, got {conflict_winner!r}."
        )
    if unmatched_present not in _VALID_CONFLICT:
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: {ctx} 'unmatched_present' must be "
            f"one of {_VALID_CONFLICT}, got {unmatched_present!r}."
        )

    pass_threshold = 0.999
    if "pass_threshold" in raw:
        try:
            pass_threshold = float(raw["pass_threshold"])
        except (TypeError, ValueError) as exc:
            raise PluginError(
                f"YAML evaluator file {str(path)!r}: {ctx} 'pass_threshold' must be "
                f"a float, got {raw['pass_threshold']!r}."
            ) from exc

    return GradedEvaluator(
        id=ev_id,
        description=description,
        areas=areas,
        success_label=success_label,
        failure_label=failure_label,
        conflict_winner=conflict_winner,  # type: ignore[arg-type]
        unmatched_present=unmatched_present,  # type: ignore[arg-type]
        pass_threshold=pass_threshold,
    )


def _parse_area(raw: Any, ctx: str, path: Path) -> Area:
    """Build an :class:`Area` from a raw mapping."""
    _require_mapping(raw, ctx, path)

    name = _require_str(raw, "name", ctx, path)
    if not name.strip():
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: {ctx} area 'name' must be non-empty."
        )

    if "presence" not in raw:
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: {ctx} area is missing 'presence'."
        )
    presence = _parse_pattern_set(raw["presence"], f"{ctx}.presence", path)

    success_raw = raw.get("success", [])
    failure_raw = raw.get("failure", [])
    if not isinstance(success_raw, list):
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: {ctx} 'success' must be a list."
        )
    if not isinstance(failure_raw, list):
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: {ctx} 'failure' must be a list."
        )

    success = [
        _parse_pattern_set(ps, f"{ctx}.success[{i}]", path)
        for i, ps in enumerate(success_raw)
    ]
    failure = [
        _parse_pattern_set(ps, f"{ctx}.failure[{i}]", path)
        for i, ps in enumerate(failure_raw)
    ]

    return Area(name=name.strip(), presence=presence, success=success, failure=failure)


# ---------------------------------------------------------------------------
# PatternSet parsing
# ---------------------------------------------------------------------------


def _parse_pattern_set(raw: Any, ctx: str, path: Path) -> PatternSet:
    """Build a :class:`PatternSet` from a raw mapping."""
    _require_mapping(raw, ctx, path)

    name = _require_str(raw, "name", ctx, path)
    if not name.strip():
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: {ctx} PatternSet 'name' must be non-empty."
        )

    patterns_raw = raw.get("patterns")
    if not isinstance(patterns_raw, list) or not patterns_raw:
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: {ctx} PatternSet 'patterns' must be "
            "a non-empty list."
        )

    patterns: list[str] = []
    for i, pat in enumerate(patterns_raw):
        if not isinstance(pat, str) or not pat:
            raise PluginError(
                f"YAML evaluator file {str(path)!r}: {ctx} PatternSet 'patterns[{i}]' "
                f"must be a non-empty string, got {pat!r}."
            )
        patterns.append(pat)

    flags = re.IGNORECASE
    if "flags" in raw:
        flags = _parse_flags(raw["flags"], ctx, path)

    try:
        return PatternSet(name=name.strip(), patterns=tuple(patterns), flags=flags)
    except ValueError as exc:
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: {ctx} PatternSet construction failed: {exc}"
        ) from exc


def _parse_flags(raw_flags: Any, ctx: str, path: Path) -> int:
    """Parse a flags value (string or list of strings) into an ``re`` flags int."""
    if isinstance(raw_flags, list):
        names = [str(f).strip().upper() for f in raw_flags if str(f).strip()]
    elif isinstance(raw_flags, str):
        names = [n.strip().upper() for n in raw_flags.replace(",", " ").split() if n.strip()]
    else:
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: {ctx} 'flags' must be a string or "
            f"list of flag names, got {type(raw_flags).__name__}."
        )

    result = 0
    for name in names:
        if name not in _FLAG_MAP:
            raise PluginError(
                f"YAML evaluator file {str(path)!r}: {ctx} unknown flag {name!r}. "
                f"Valid flags: {', '.join(sorted(_FLAG_MAP))}."
            )
        result |= _FLAG_MAP[name]
    return result


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _require_mapping(raw: Any, ctx: str, path: Path) -> None:
    if not isinstance(raw, dict):
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: {ctx} must be a mapping, "
            f"got {type(raw).__name__}."
        )


def _require_str(raw: dict, key: str, ctx: str, path: Path) -> str:
    if key not in raw:
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: {ctx} is missing required key {key!r}."
        )
    value = raw[key]
    if not isinstance(value, str):
        raise PluginError(
            f"YAML evaluator file {str(path)!r}: {ctx}.{key} must be a string, "
            f"got {type(value).__name__}."
        )
    return value
