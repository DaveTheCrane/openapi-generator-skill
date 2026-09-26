"""Parser for Kiro spec-driven tasklist markdown files.

Handles the two formats seen across Kiro versions:

* **Flat style** — ``## Task N: Title`` headers, each followed by ``- [ ] ...``
  detail bullets. Those bullets are *body lines* of the task, not sub-tasks.
  The task id is ``"N"``.

* **Nested style** — top-level ``- [ ] N. Title`` checkbox items with indented
  ``- [ ] N.M ...`` sub-tasks; more-deeply-indented ``- ...`` lines are body
  lines of their parent sub-task. Ids look like ``"1"`` or ``"1.2"``.

Optional ``## Overview``, ``## Notes``, and a ``## Task Dependency Graph``
fenced ```json block are all tolerated whether present, absent, or malformed.

Checkbox state is parsed and stored on each :class:`~tasklist_eval.models.Task`
but is IGNORED by evaluators when computing verdicts.
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path

from .exceptions import TasklistParseError
from .models import Task, TaskList

# `- [ ] N. Title` / `- [x]* 1.2 Title` — leading indent captured to derive depth.
_CHECKBOX_RE = re.compile(
    r"^(?P<indent>\s*)-\s*\[(?P<mark>.?)\](?P<opt>\*?)\s*"
    r"(?P<num>\d+(?:\.\d+)*)\.?\s*(?P<title>.*)$"
)
# A plain bullet (no checkbox) — treated as a body/detail line.
_BULLET_RE = re.compile(r"^(?P<indent>\s*)-\s+(?P<text>.*)$")
# `## Task N: Title` flat-style header.
_FLAT_TASK_RE = re.compile(
    r"^##\s+Task\s+(?P<num>\d+)\s*[:\-.]?\s*(?P<title>.*)$", re.IGNORECASE | re.MULTILINE
)
# `_Requirements: 1.1, 2.3_` italicized requirement references.
_REQUIREMENTS_RE = re.compile(r"_?Requirements:\s*(?P<refs>[^_]*)_?", re.IGNORECASE)


def _parse_requirements(text: str) -> list[str]:
    """Extract requirement reference tokens from a ``_Requirements: ..._`` line."""
    match = _REQUIREMENTS_RE.search(text)
    if not match:
        return []
    refs = match.group("refs")
    # Split on commas and whitespace; keep dotted tokens like 1.1, 10.2.
    tokens = re.split(r"[,\s]+", refs.strip().rstrip("_").strip())
    return [t for t in tokens if t]


def _is_requirements_line(text: str) -> bool:
    stripped = text.strip()
    return stripped.lower().startswith("_requirements:") or stripped.lower().startswith(
        "requirements:"
    )


def _extract_section(lines: list[str], heading: str) -> list[str]:
    """Return the raw lines under a ``## heading`` up to the next ``## `` heading."""
    out: list[str] = []
    capturing = False
    for line in lines:
        if line.startswith("## "):
            if capturing:
                break
            if line[3:].strip().lower() == heading.lower():
                capturing = True
                continue
        elif capturing:
            out.append(line)
    return out


def _parse_overview(lines: list[str]) -> str:
    body = _extract_section(lines, "Overview")
    return "\n".join(line for line in body).strip()


def _parse_notes(lines: list[str]) -> list[str]:
    """Return bullet strings under a ``## Notes`` section (empty list if absent)."""
    notes: list[str] = []
    for line in _extract_section(lines, "Notes"):
        m = _BULLET_RE.match(line)
        if m:
            notes.append(m.group("text").strip())
    return notes


def _parse_dependency_graph(raw: str) -> dict | None:
    """Return the JSON object in a ``## Task Dependency Graph`` fenced block.

    Returns ``None`` if the section, the fenced block, or valid JSON is absent
    (malformed JSON is tolerated → ``None`` rather than raising).
    """
    # Find the heading, then the first ```json ... ``` fence after it.
    heading = re.search(r"^##\s+Task Dependency Graph\s*$", raw, re.MULTILINE)
    if not heading:
        return None
    tail = raw[heading.end():]
    fence = re.search(r"```(?:json)?\s*\n(?P<body>.*?)```", tail, re.DOTALL)
    if not fence:
        return None
    try:
        parsed = json.loads(fence.group("body"))
    except (json.JSONDecodeError, ValueError):
        return None
    return parsed if isinstance(parsed, dict) else None


def _indent_width(indent: str) -> int:
    """Return a normalized indent width (tabs counted as two spaces)."""
    return len(indent.replace("\t", "  "))


def _normalize_mark(mark: str) -> str | None:
    """Normalize a raw checkbox marker; empty bracket ``[]`` → space."""
    if mark == "":
        return " "
    return mark


def _parse_nested_tasks(lines: list[str]) -> list[Task]:
    """Parse nested ``- [ ] N.M`` checkbox tasks into a Task tree.

    Uses a stack keyed by indentation. Checkbox items become Tasks; plain
    bullets and ``_Requirements:_`` lines attach to the nearest enclosing Task.
    """
    root: list[Task] = []
    # stack entries: (indent_width, Task)
    stack: list[tuple[int, Task]] = []

    for line in lines:
        if not line.strip():
            continue

        cb = _CHECKBOX_RE.match(line)
        if cb:
            indent = _indent_width(cb.group("indent"))
            task = Task(
                id=cb.group("num"),
                title=cb.group("title").strip(),
                checkbox=_normalize_mark(cb.group("mark")),
                optional=bool(cb.group("opt")),
            )
            # Pop until we find a shallower parent.
            while stack and stack[-1][0] >= indent:
                stack.pop()
            if stack:
                stack[-1][1].children.append(task)
            else:
                root.append(task)
            stack.append((indent, task))
            continue

        bullet = _BULLET_RE.match(line)
        if bullet and stack:
            text = bullet.group("text").strip()
            target = stack[-1][1]
            if _is_requirements_line(text):
                target.requirements.extend(_parse_requirements(text))
            else:
                target.body_lines.append(text)
            continue

        # Non-bullet continuation lines (e.g. a **Property** line) attach as
        # body to the nearest task if we are inside one.
        if stack:
            text = line.strip()
            target = stack[-1][1]
            if _is_requirements_line(text):
                target.requirements.extend(_parse_requirements(text))
            elif text:
                target.body_lines.append(text)

    return root


def _parse_flat_tasks(lines: list[str]) -> list[Task]:
    """Parse flat ``## Task N:`` headers with following detail bullets."""
    tasks: list[Task] = []
    current: Task | None = None

    for line in lines:
        header = _FLAT_TASK_RE.match(line)
        if header:
            current = Task(
                id=header.group("num"),
                title=header.group("title").strip(),
                checkbox=None,           # flat headers carry no checkbox of their own
            )
            tasks.append(current)
            continue

        if current is None:
            continue

        # Detail bullets under a flat task become body lines (not sub-tasks).
        cb = _CHECKBOX_RE.match(line)
        if cb:
            text = cb.group("title").strip()
            if _is_requirements_line(text):
                current.requirements.extend(_parse_requirements(text))
            else:
                current.body_lines.append(text)
            continue
        bullet = _BULLET_RE.match(line)
        if bullet:
            text = bullet.group("text").strip()
            if _is_requirements_line(text):
                current.requirements.extend(_parse_requirements(text))
            else:
                current.body_lines.append(text)
            continue
        stripped = line.strip()
        if stripped and _is_requirements_line(stripped):
            current.requirements.extend(_parse_requirements(stripped))
        elif stripped:
            current.body_lines.append(stripped)

    return tasks


def _is_flat_style(raw: str) -> bool:
    """True when the document uses ``## Task N:`` headers."""
    return bool(_FLAT_TASK_RE.search(raw))


def _tasks_region(lines: list[str]) -> list[str]:
    """Return the lines belonging to the task list region for nested parsing.

    Starts after a ``## Tasks`` heading if present, otherwise from the top;
    stops at the ``## Notes`` or ``## Task Dependency Graph`` sections.
    """
    start = 0
    for i, line in enumerate(lines):
        if line.strip().lower() == "## tasks":
            start = i + 1
            break
    region: list[str] = []
    for line in lines[start:]:
        if line.startswith("## ") and line[3:].strip().lower() in (
            "notes",
            "task dependency graph",
        ):
            break
        region.append(line)
    return region


def parse_tasklist(path: str) -> TaskList:
    """Parse a tasklist markdown file at *path* into a :class:`TaskList`.

    Raises
    ------
    TasklistParseError
        If the file does not exist, is not readable, or is empty.
    """
    p = Path(path)
    if not p.exists() or not p.is_file():
        raise TasklistParseError(f"tasklist file does not exist: {path!r}")
    if not os.access(p, os.R_OK):
        raise TasklistParseError(f"tasklist file is not readable: {path!r}")

    try:
        raw = p.read_text(encoding="utf-8")
    except OSError as exc:
        raise TasklistParseError(f"failed to read tasklist {path!r}: {exc}") from exc

    if not raw.strip():
        raise TasklistParseError(f"tasklist file is empty: {path!r}")

    lines = raw.splitlines()

    # Title from the first `# ` heading (not `## `).
    title = ""
    for line in lines:
        if line.startswith("# ") and not line.startswith("## "):
            title = line[2:].strip()
            break

    overview = _parse_overview(lines)
    notes = _parse_notes(lines)
    dependency_graph = _parse_dependency_graph(raw)

    if _is_flat_style(raw):
        tasks = _parse_flat_tasks(lines)
    else:
        tasks = _parse_nested_tasks(_tasks_region(lines))

    return TaskList(
        title=title,
        overview=overview,
        tasks=tasks,
        notes=notes,
        dependency_graph=dependency_graph,
        raw=raw,
    )
