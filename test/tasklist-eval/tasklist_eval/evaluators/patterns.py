"""Named, pre-compiled regex pattern sets.

A :class:`PatternSet` is the building block of the generic evaluators: a named,
ordered group of regexes. The name shows up in evidence bullets and in the
structured ``details`` of a result, so reports say *which* kind of signal fired
(e.g. ``server-handcoded``) rather than just the matched text.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Iterable, Union

from ..models import TaskList

PatternLike = Union[str, "re.Pattern[str]"]


@dataclass(frozen=True)
class PatternSet:
    """A named, ordered set of regexes.

    ``patterns`` may contain pattern strings (compiled with ``flags``, which
    default to ``re.IGNORECASE``) and/or pre-compiled ``re.Pattern`` objects,
    which keep their own flags. That lets a single set mix case-insensitive
    and case-sensitive patterns.
    """

    name: str
    patterns: tuple[PatternLike, ...]
    flags: int = re.IGNORECASE
    compiled: tuple["re.Pattern[str]", ...] = field(
        init=False, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        if not isinstance(self.name, str) or not self.name.strip():
            raise ValueError("PatternSet name must be a non-empty string")

        if isinstance(self.patterns, (str, re.Pattern)):
            raw: tuple = (self.patterns,)
        else:
            raw = tuple(self.patterns)
        if not raw:
            raise ValueError(f"PatternSet '{self.name}' must have at least one pattern")
        object.__setattr__(self, "patterns", raw)

        compiled: list[re.Pattern[str]] = []
        for pat in raw:
            if isinstance(pat, re.Pattern):
                compiled.append(pat)
                continue
            if not isinstance(pat, str) or not pat:
                raise ValueError(
                    f"PatternSet '{self.name}': invalid pattern {pat!r} "
                    "(expected a non-empty string or compiled re.Pattern)"
                )
            try:
                compiled.append(re.compile(pat, self.flags))
            except re.error as exc:
                raise ValueError(
                    f"PatternSet '{self.name}': invalid regex {pat!r}: {exc}"
                ) from exc
        object.__setattr__(self, "compiled", tuple(compiled))

    def search(self, text: str) -> str | None:
        """Return the first matched substring across the patterns, in order."""
        for pat in self.compiled:
            m = pat.search(text)
            if m:
                return m.group(0)
        return None


def find_in_tasks(
    pattern_set: PatternSet, tasks: TaskList | Iterable
) -> list[tuple[str, str]]:
    """Return ``(task_id, matched_text)`` for each task whose text matches.

    *tasks* may be a :class:`TaskList` (all tasks, flattened) or any iterable of
    tasks. At most one match is recorded per task; the task id is ``"?"`` when
    the task has no id.
    """
    iterable = tasks.iter_tasks() if isinstance(tasks, TaskList) else tasks
    hits: list[tuple[str, str]] = []
    for task in iterable:
        m = pattern_set.search(task.all_text())
        if m is not None:
            hits.append((task.id if task.id is not None else "?", m))
    return hits
