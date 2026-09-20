"""Unit tests for test/harness/fixture_loader.py."""

from __future__ import annotations

import textwrap

import pytest

from harness.exceptions import FixtureLoadError
from harness.fixture_loader import load_fixture
from harness.models import ExpectedOutcome, PromptCase


# --------------------------------------------------------------------------- #
# Helpers                                                                       #
# --------------------------------------------------------------------------- #


def _write_fixture(tmp_path, content: str, filename: str = "fixture.yaml") -> str:
    """Write *content* to a temp file and return its path as a string."""
    p = tmp_path / filename
    p.write_text(content, encoding="utf-8")
    return str(p)


MINIMAL_FIXTURE = textwrap.dedent("""\
    skill: test-skill

    cases:
      - id: case-one
        prompt: "Create a Spring Boot microservice from this OpenAPI spec"
        expected: activate
        notes: "Core use case"

      - id: case-two
        prompt: "How do I write a for loop in Java?"
        expected: no_activate
""")

SINGLE_CASE_ACTIVATE = textwrap.dedent("""\
    cases:
      - id: only-case
        prompt: "Generate a REST API from an OpenAPI spec"
        expected: activate
""")

SINGLE_CASE_NO_ACTIVATE = textwrap.dedent("""\
    cases:
      - id: only-case
        prompt: "Tell me about Python decorators"
        expected: no_activate
""")


# --------------------------------------------------------------------------- #
# Happy-path tests                                                               #
# --------------------------------------------------------------------------- #


class TestLoadFixtureHappyPath:
    def test_returns_list_of_prompt_cases(self, tmp_path):
        path = _write_fixture(tmp_path, MINIMAL_FIXTURE)
        result = load_fixture(path)
        assert isinstance(result, list)
        assert all(isinstance(c, PromptCase) for c in result)

    def test_correct_count(self, tmp_path):
        path = _write_fixture(tmp_path, MINIMAL_FIXTURE)
        result = load_fixture(path)
        assert len(result) == 2

    def test_id_extracted(self, tmp_path):
        path = _write_fixture(tmp_path, MINIMAL_FIXTURE)
        result = load_fixture(path)
        assert result[0].id == "case-one"
        assert result[1].id == "case-two"

    def test_prompt_extracted(self, tmp_path):
        path = _write_fixture(tmp_path, MINIMAL_FIXTURE)
        result = load_fixture(path)
        assert "Spring Boot" in result[0].prompt
        assert "for loop" in result[1].prompt

    def test_expected_activate_mapped(self, tmp_path):
        path = _write_fixture(tmp_path, SINGLE_CASE_ACTIVATE)
        result = load_fixture(path)
        assert result[0].expected == ExpectedOutcome.ACTIVATE

    def test_expected_no_activate_mapped(self, tmp_path):
        path = _write_fixture(tmp_path, SINGLE_CASE_NO_ACTIVATE)
        result = load_fixture(path)
        assert result[0].expected == ExpectedOutcome.NO_ACTIVATE

    def test_notes_optional_present(self, tmp_path):
        path = _write_fixture(tmp_path, MINIMAL_FIXTURE)
        result = load_fixture(path)
        assert result[0].notes == "Core use case"

    def test_notes_optional_absent(self, tmp_path):
        path = _write_fixture(tmp_path, MINIMAL_FIXTURE)
        result = load_fixture(path)
        assert result[1].notes is None

    def test_skill_key_is_ignored(self, tmp_path):
        """Top-level 'skill' field is informational and must not cause errors."""
        path = _write_fixture(tmp_path, MINIMAL_FIXTURE)
        result = load_fixture(path)
        assert len(result) == 2

    def test_no_top_level_skill_key_is_fine(self, tmp_path):
        content = textwrap.dedent("""\
            cases:
              - id: a
                prompt: "Some prompt"
                expected: activate
        """)
        path = _write_fixture(tmp_path, content)
        result = load_fixture(path)
        assert len(result) == 1

    def test_valid_id_patterns(self, tmp_path):
        """IDs with letters, digits, hyphens, and underscores are all valid."""
        for case_id in ["abc", "abc-def", "abc_def", "ABC123", "a1-b2_c3"]:
            content = f"cases:\n  - id: {case_id}\n    prompt: test\n    expected: activate\n"
            path = _write_fixture(tmp_path, content)
            result = load_fixture(path)
            assert result[0].id == case_id

    def test_order_preserved(self, tmp_path):
        content = textwrap.dedent("""\
            cases:
              - id: first
                prompt: First prompt
                expected: activate
              - id: second
                prompt: Second prompt
                expected: no_activate
              - id: third
                prompt: Third prompt
                expected: activate
        """)
        path = _write_fixture(tmp_path, content)
        result = load_fixture(path)
        assert [c.id for c in result] == ["first", "second", "third"]


# --------------------------------------------------------------------------- #
# Error-path tests: file-level                                                  #
# --------------------------------------------------------------------------- #


class TestLoadFixtureFileErrors:
    def test_missing_file_raises(self, tmp_path):
        with pytest.raises(FixtureLoadError, match="Cannot read"):
            load_fixture(str(tmp_path / "nonexistent.yaml"))

    def test_invalid_yaml_raises(self, tmp_path):
        path = _write_fixture(tmp_path, "cases: [broken: yaml: here")
        with pytest.raises(FixtureLoadError, match="valid YAML"):
            load_fixture(path)

    def test_non_mapping_top_level_raises(self, tmp_path):
        path = _write_fixture(tmp_path, "- just a list item\n")
        with pytest.raises(FixtureLoadError):
            load_fixture(path)

    def test_empty_file_raises(self, tmp_path):
        path = _write_fixture(tmp_path, "")
        with pytest.raises(FixtureLoadError):
            load_fixture(path)

    def test_missing_cases_key_raises(self, tmp_path):
        path = _write_fixture(tmp_path, "skill: test-skill\n")
        with pytest.raises(FixtureLoadError, match="cases"):
            load_fixture(path)

    def test_empty_cases_list_raises(self, tmp_path):
        path = _write_fixture(tmp_path, "cases: []\n")
        with pytest.raises(FixtureLoadError, match="cases"):
            load_fixture(path)

    def test_null_cases_raises(self, tmp_path):
        path = _write_fixture(tmp_path, "cases:\n")
        with pytest.raises(FixtureLoadError, match="cases"):
            load_fixture(path)

    def test_cases_not_a_list_raises(self, tmp_path):
        path = _write_fixture(tmp_path, "cases: not-a-list\n")
        with pytest.raises(FixtureLoadError):
            load_fixture(path)


# --------------------------------------------------------------------------- #
# Error-path tests: missing required fields                                     #
# --------------------------------------------------------------------------- #


class TestLoadFixtureMissingFields:
    def test_missing_id_raises(self, tmp_path):
        content = textwrap.dedent("""\
            cases:
              - prompt: "A prompt without an id"
                expected: activate
        """)
        path = _write_fixture(tmp_path, content)
        with pytest.raises(FixtureLoadError, match="'id'"):
            load_fixture(path)

    def test_missing_prompt_raises(self, tmp_path):
        content = textwrap.dedent("""\
            cases:
              - id: no-prompt
                expected: activate
        """)
        path = _write_fixture(tmp_path, content)
        with pytest.raises(FixtureLoadError, match="'prompt'"):
            load_fixture(path)

    def test_missing_expected_raises(self, tmp_path):
        content = textwrap.dedent("""\
            cases:
              - id: no-expected
                prompt: "A prompt without expected"
        """)
        path = _write_fixture(tmp_path, content)
        with pytest.raises(FixtureLoadError, match="'expected'"):
            load_fixture(path)

    def test_missing_field_identifies_index(self, tmp_path):
        """Error message should reference the case index."""
        content = textwrap.dedent("""\
            cases:
              - id: good-case
                prompt: Fine
                expected: activate
              - prompt: "Missing id at index 1"
                expected: no_activate
        """)
        path = _write_fixture(tmp_path, content)
        with pytest.raises(FixtureLoadError, match="index 1"):
            load_fixture(path)

    def test_empty_id_raises(self, tmp_path):
        content = textwrap.dedent("""\
            cases:
              - id: ""
                prompt: "Empty id"
                expected: activate
        """)
        path = _write_fixture(tmp_path, content)
        with pytest.raises(FixtureLoadError, match="empty"):
            load_fixture(path)

    def test_empty_prompt_raises(self, tmp_path):
        content = textwrap.dedent("""\
            cases:
              - id: empty-prompt
                prompt: ""
                expected: activate
        """)
        path = _write_fixture(tmp_path, content)
        with pytest.raises(FixtureLoadError, match="empty"):
            load_fixture(path)


# --------------------------------------------------------------------------- #
# Error-path tests: invalid field values                                        #
# --------------------------------------------------------------------------- #


class TestLoadFixtureInvalidValues:
    def test_invalid_expected_value_raises(self, tmp_path):
        content = textwrap.dedent("""\
            cases:
              - id: bad-expected
                prompt: "Some prompt"
                expected: maybe
        """)
        path = _write_fixture(tmp_path, content)
        with pytest.raises(FixtureLoadError, match="maybe"):
            load_fixture(path)

    def test_invalid_expected_empty_raises(self, tmp_path):
        content = textwrap.dedent("""\
            cases:
              - id: empty-expected
                prompt: "Some prompt"
                expected: ""
        """)
        path = _write_fixture(tmp_path, content)
        with pytest.raises(FixtureLoadError):
            load_fixture(path)

    def test_invalid_expected_boolean_raises(self, tmp_path):
        content = textwrap.dedent("""\
            cases:
              - id: bool-expected
                prompt: "Some prompt"
                expected: true
        """)
        path = _write_fixture(tmp_path, content)
        with pytest.raises(FixtureLoadError):
            load_fixture(path)

    def test_id_with_spaces_raises(self, tmp_path):
        content = textwrap.dedent("""\
            cases:
              - id: "has spaces"
                prompt: "Some prompt"
                expected: activate
        """)
        path = _write_fixture(tmp_path, content)
        with pytest.raises(FixtureLoadError, match="invalid 'id'"):
            load_fixture(path)

    def test_id_with_dots_raises(self, tmp_path):
        content = textwrap.dedent("""\
            cases:
              - id: has.dot
                prompt: "Some prompt"
                expected: activate
        """)
        path = _write_fixture(tmp_path, content)
        with pytest.raises(FixtureLoadError, match="invalid 'id'"):
            load_fixture(path)


# --------------------------------------------------------------------------- #
# Error-path tests: duplicate IDs                                               #
# --------------------------------------------------------------------------- #


class TestLoadFixtureDuplicateIds:
    def test_duplicate_id_raises(self, tmp_path):
        content = textwrap.dedent("""\
            cases:
              - id: duplicate
                prompt: "First occurrence"
                expected: activate
              - id: duplicate
                prompt: "Second occurrence"
                expected: no_activate
        """)
        path = _write_fixture(tmp_path, content)
        with pytest.raises(FixtureLoadError, match="duplicate"):
            load_fixture(path)

    def test_duplicate_id_names_the_duplicate(self, tmp_path):
        content = textwrap.dedent("""\
            cases:
              - id: my-case
                prompt: "First"
                expected: activate
              - id: other-case
                prompt: "Middle"
                expected: no_activate
              - id: my-case
                prompt: "Duplicate of first"
                expected: activate
        """)
        path = _write_fixture(tmp_path, content)
        with pytest.raises(FixtureLoadError, match="my-case"):
            load_fixture(path)

    def test_unique_ids_do_not_raise(self, tmp_path):
        content = textwrap.dedent("""\
            cases:
              - id: a
                prompt: "First"
                expected: activate
              - id: b
                prompt: "Second"
                expected: no_activate
              - id: c
                prompt: "Third"
                expected: activate
        """)
        path = _write_fixture(tmp_path, content)
        result = load_fixture(path)
        assert len(result) == 3
