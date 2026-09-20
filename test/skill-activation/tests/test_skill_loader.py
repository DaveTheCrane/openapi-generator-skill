"""Unit tests for test/harness/skill_loader.py."""

from __future__ import annotations

import textwrap

import pytest

from harness.exceptions import SkillLoadError
from harness.models import SkillDefinition
from harness.skill_loader import load_skill


# --------------------------------------------------------------------------- #
# Helpers                                                                      #
# --------------------------------------------------------------------------- #


def _write_skill(tmp_path, content: str, filename: str = "SKILL.md") -> str:
    """Write *content* to a temp file and return its path as a string."""
    p = tmp_path / filename
    p.write_text(content, encoding="utf-8")
    return str(p)


MINIMAL_SKILL = textwrap.dedent("""\
    ---
    description: A minimal test skill.
    ---

    # Test Skill

    ## When to Use

    Use this skill when writing tests.
""")

FOLDED_DESCRIPTION_SKILL = textwrap.dedent("""\
    ---
    description: >
      Generates a RESTful Spring Boot microservice from an OpenAPI specification
      using the openapi-generator-maven-plugin with the delegate pattern.
    ---

    # Spring Boot OpenAPI Generator Skill

    ## When to Use

    - User asks to create a Spring Boot REST microservice from an OpenAPI spec
    - User needs HTTP client libraries for downstream services

    ## Prerequisites

    The target project must be a Maven-based Spring Boot application.
""")

NAMED_SKILL = textwrap.dedent("""\
    ---
    name: my-custom-skill
    description: Custom skill with explicit name.
    ---

    ## When to Use

    Use when testing named skills.
""")


# --------------------------------------------------------------------------- #
# Happy-path tests                                                              #
# --------------------------------------------------------------------------- #


class TestLoadSkillHappyPath:
    def test_returns_skill_definition(self, tmp_path):
        path = _write_skill(tmp_path, MINIMAL_SKILL)
        result = load_skill(path)
        assert isinstance(result, SkillDefinition)

    def test_description_extracted(self, tmp_path):
        path = _write_skill(tmp_path, MINIMAL_SKILL)
        result = load_skill(path)
        assert result.description == "A minimal test skill."

    def test_when_to_use_extracted(self, tmp_path):
        path = _write_skill(tmp_path, MINIMAL_SKILL)
        result = load_skill(path)
        assert "Use this skill when writing tests." in result.when_to_use

    def test_raw_content_is_verbatim(self, tmp_path):
        path = _write_skill(tmp_path, MINIMAL_SKILL)
        result = load_skill(path)
        assert result.raw_content == MINIMAL_SKILL

    def test_name_from_front_matter(self, tmp_path):
        path = _write_skill(tmp_path, NAMED_SKILL)
        result = load_skill(path)
        assert result.name == "my-custom-skill"

    def test_name_falls_back_to_directory(self, tmp_path):
        """When filename is SKILL.md and front matter has no name, use parent dir."""
        path = _write_skill(tmp_path, MINIMAL_SKILL)
        result = load_skill(path)
        # parent dir name is tmp_path's last component
        import os
        expected = os.path.basename(str(tmp_path))
        assert result.name == expected

    def test_name_falls_back_to_filename_stem(self, tmp_path):
        """When a non-SKILL filename is used, fall back to the stem."""
        path = _write_skill(tmp_path, MINIMAL_SKILL, filename="my-skill.md")
        result = load_skill(path)
        assert result.name == "my-skill"

    def test_folded_description_normalised(self, tmp_path):
        """Folded YAML scalar (>) should produce a single trimmed string."""
        path = _write_skill(tmp_path, FOLDED_DESCRIPTION_SKILL)
        result = load_skill(path)
        # No leading/trailing whitespace
        assert result.description == result.description.strip()
        assert len(result.description) > 0

    def test_when_to_use_excludes_next_section(self, tmp_path):
        """The ## When to Use body must NOT bleed into the next ## section."""
        path = _write_skill(tmp_path, FOLDED_DESCRIPTION_SKILL)
        result = load_skill(path)
        assert "Prerequisites" not in result.when_to_use

    def test_when_to_use_includes_all_bullet_points(self, tmp_path):
        path = _write_skill(tmp_path, FOLDED_DESCRIPTION_SKILL)
        result = load_skill(path)
        assert "OpenAPI spec" in result.when_to_use
        assert "HTTP client libraries" in result.when_to_use

    def test_case_insensitive_when_to_use_heading(self, tmp_path):
        """## WHEN TO USE and ## when to use should both be recognised."""
        content = textwrap.dedent("""\
            ---
            description: Case test skill.
            ---

            ## WHEN TO USE

            Uppercase heading works fine.
        """)
        path = _write_skill(tmp_path, content)
        result = load_skill(path)
        assert "Uppercase heading works fine." in result.when_to_use

    def test_real_springboot_skill(self):
        """Smoke-test against the actual SKILL.md in this repo."""
        import os
        repo_root = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
        real_path = os.path.join(repo_root, "springboot-openapi-generator", "SKILL.md")
        if not os.path.exists(real_path):
            pytest.skip("Real SKILL.md not found — skipping smoke test")
        result = load_skill(real_path)
        assert result.name == "springboot-openapi-generator"
        assert result.description
        assert result.when_to_use
        assert result.raw_content


# --------------------------------------------------------------------------- #
# Error-path tests                                                              #
# --------------------------------------------------------------------------- #


class TestLoadSkillErrors:
    def test_missing_file_raises_skill_load_error(self, tmp_path):
        with pytest.raises(SkillLoadError, match="Cannot read"):
            load_skill(str(tmp_path / "nonexistent.md"))

    def test_missing_description_raises_skill_load_error(self, tmp_path):
        content = textwrap.dedent("""\
            ---
            name: no-desc-skill
            ---

            ## When to Use

            Use it anyway.
        """)
        path = _write_skill(tmp_path, content)
        with pytest.raises(SkillLoadError, match="description"):
            load_skill(path)

    def test_missing_when_to_use_raises_skill_load_error(self, tmp_path):
        content = textwrap.dedent("""\
            ---
            description: Has description but no when-to-use.
            ---

            ## Other Section

            Some content here.
        """)
        path = _write_skill(tmp_path, content)
        with pytest.raises(SkillLoadError, match="When to Use"):
            load_skill(path)

    def test_empty_when_to_use_raises_skill_load_error(self, tmp_path):
        content = textwrap.dedent("""\
            ---
            description: Empty section test.
            ---

            ## When to Use

            ## Next Section

            Content here.
        """)
        path = _write_skill(tmp_path, content)
        with pytest.raises(SkillLoadError, match="empty"):
            load_skill(path)

    def test_missing_front_matter_raises_skill_load_error(self, tmp_path):
        content = "# No front matter here\n\n## When to Use\n\nSomething.\n"
        path = _write_skill(tmp_path, content)
        with pytest.raises(SkillLoadError):
            load_skill(path)

    def test_unclosed_front_matter_raises_skill_load_error(self, tmp_path):
        content = textwrap.dedent("""\
            ---
            description: Unclosed front matter.

            ## When to Use

            Content.
        """)
        path = _write_skill(tmp_path, content)
        with pytest.raises(SkillLoadError, match="unclosed"):
            load_skill(path)

    def test_invalid_yaml_in_front_matter_raises_skill_load_error(self, tmp_path):
        content = textwrap.dedent("""\
            ---
            description: [broken yaml
            ---

            ## When to Use

            Content.
        """)
        path = _write_skill(tmp_path, content)
        with pytest.raises(SkillLoadError, match="invalid YAML"):
            load_skill(path)
