"""Skill loader — parses a SKILL.md file into a SkillDefinition."""

from __future__ import annotations

import os
import re

import yaml

from .exceptions import SkillLoadError
from .models import SkillDefinition


def load_skill(path: str) -> SkillDefinition:
    """Read and parse a SKILL.md file, returning a :class:`SkillDefinition`.

    Args:
        path: Path to the SKILL.md file.

    Returns:
        A fully-populated :class:`SkillDefinition`.

    Raises:
        SkillLoadError: If the file is missing a ``description`` field in its
            YAML front matter, or is missing a ``## When to Use`` section.
    """
    try:
        with open(path, "r", encoding="utf-8") as fh:
            raw_content = fh.read()
    except OSError as exc:
        raise SkillLoadError(f"Cannot read skill file '{path}': {exc}") from exc

    # ------------------------------------------------------------------ #
    # 1. Parse YAML front matter                                           #
    # ------------------------------------------------------------------ #
    front_matter, body = _split_front_matter(raw_content, path)

    description = front_matter.get("description")
    if not description:
        raise SkillLoadError(
            f"Skill file '{path}' is missing a 'description' field in its YAML front matter."
        )
    # PyYAML folds multi-line scalars (>) by collapsing newlines into spaces
    # and may leave trailing whitespace — normalise to a clean single string.
    description = str(description).strip()

    # ------------------------------------------------------------------ #
    # 2. Extract ## When to Use section                                    #
    # ------------------------------------------------------------------ #
    when_to_use = _extract_when_to_use(body, path)

    # ------------------------------------------------------------------ #
    # 3. Derive name from the front matter or fall back to the filename   #
    # ------------------------------------------------------------------ #
    name = str(front_matter.get("name", "")).strip()
    if not name:
        # e.g. "springboot-openapi-generator" from "SKILL.md" → parent dir name
        name = os.path.splitext(os.path.basename(path))[0]
        if name.upper() == "SKILL":
            # Use the containing directory name as the skill name
            name = os.path.basename(os.path.dirname(os.path.abspath(path)))

    return SkillDefinition(
        name=name,
        description=description,
        when_to_use=when_to_use,
        raw_content=raw_content,
    )


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #


def _split_front_matter(content: str, path: str) -> tuple[dict, str]:
    """Split ``content`` into (front_matter_dict, body_text).

    The front matter must be delimited by ``---`` markers.  The opening ``---``
    must be the very first line (ignoring a leading UTF-8 BOM).
    """
    # Strip BOM if present
    content_stripped = content.lstrip("\ufeff")

    if not content_stripped.startswith("---"):
        raise SkillLoadError(
            f"Skill file '{path}' does not start with a YAML front matter block ('---')."
        )

    # Find the closing '---'
    # The opening delimiter is the first line; search from the character
    # immediately after it.
    first_delim_end = content_stripped.index("\n") + 1
    close_match = re.search(r"^---\s*$", content_stripped[first_delim_end:], re.MULTILINE)
    if close_match is None:
        raise SkillLoadError(
            f"Skill file '{path}' has an unclosed YAML front matter block (missing closing '---')."
        )

    fm_text = content_stripped[first_delim_end : first_delim_end + close_match.start()]
    body = content_stripped[first_delim_end + close_match.end() :]

    try:
        front_matter = yaml.safe_load(fm_text) or {}
    except yaml.YAMLError as exc:
        raise SkillLoadError(
            f"Skill file '{path}' has invalid YAML in its front matter: {exc}"
        ) from exc

    if not isinstance(front_matter, dict):
        raise SkillLoadError(
            f"Skill file '{path}' front matter must be a YAML mapping, got {type(front_matter).__name__}."
        )

    return front_matter, body


def _extract_when_to_use(body: str, path: str) -> str:
    """Return the text body of the ``## When to Use`` section.

    The section ends at the next ``##``-level heading or at end-of-file.
    """
    # Match the heading line (case-insensitive, optional trailing whitespace)
    heading_pattern = re.compile(r"^##\s+When to Use\s*$", re.IGNORECASE | re.MULTILINE)
    match = heading_pattern.search(body)
    if match is None:
        raise SkillLoadError(
            f"Skill file '{path}' is missing a '## When to Use' section."
        )

    section_start = match.end()

    # The section ends at the next ## heading or EOF
    next_heading = re.search(r"^##\s+", body[section_start:], re.MULTILINE)
    if next_heading is not None:
        section_text = body[section_start : section_start + next_heading.start()]
    else:
        section_text = body[section_start:]

    when_to_use = section_text.strip()
    if not when_to_use:
        raise SkillLoadError(
            f"Skill file '{path}' has an empty '## When to Use' section."
        )

    return when_to_use
