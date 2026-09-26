"""Tests for the tasklist parser across all three sample formats."""

from __future__ import annotations

import os

import pytest

from tasklist_eval.exceptions import TasklistParseError
from tasklist_eval.parser import parse_tasklist


def test_flat_style_activated(activated_path):
    tl = parse_tasklist(activated_path)
    assert tl.title == "Tasks: Customer Service API"
    # Flat `## Task N:` headers → 8 top-level tasks, no nesting.
    assert len(tl.tasks) == 8
    ids = [t.id for t in tl.tasks]
    assert ids == ["1", "2", "3", "4", "5", "6", "7", "8"]
    assert all(not t.children for t in tl.tasks)
    # Detail bullets are body lines, not sub-tasks.
    task2 = tl.tasks[1]
    assert any("openapi-generator-maven-plugin" in line for line in task2.body_lines)
    # No Notes / dependency graph in this sample.
    assert tl.notes == []
    assert tl.dependency_graph is None


def test_flat_checkbox_state_parsed_but_present(activated_path):
    tl = parse_tasklist(activated_path)
    # Flat headers carry no checkbox of their own; the [x] bullets become body.
    task1 = tl.tasks[0]
    assert task1.checkbox is None
    assert any("feature branch" in line.lower() for line in task1.body_lines)


def test_nested_style_not_present(not_present_path):
    tl = parse_tasklist(not_present_path)
    assert tl.title == "Implementation Plan: Customer Service API"
    assert tl.overview  # has an Overview section
    # 7 top-level nested items.
    assert len(tl.tasks) == 7
    ids = [t.id for t in tl.tasks]
    assert ids == ["1", "2", "3", "4", "5", "6", "7"]
    # Task 1 has sub-tasks 1.1 .. 1.4.
    task1 = tl.tasks[0]
    child_ids = [c.id for c in task1.children]
    assert child_ids == ["1.1", "1.2", "1.3", "1.4"]
    # Checkbox marker recorded (all [x] in this sample).
    assert task1.checkbox == "x"
    assert task1.children[0].checkbox == "x"


def test_nested_requirements_parsed(not_present_path):
    tl = parse_tasklist(not_present_path)
    task1_1 = tl.tasks[0].children[0]
    # `_Requirements: 10.1, 10.2, 10.4_`
    assert "10.1" in task1_1.requirements
    assert "10.2" in task1_1.requirements
    assert "10.4" in task1_1.requirements


def test_nested_notes_and_dependency_graph(not_present_path):
    tl = parse_tasklist(not_present_path)
    assert len(tl.notes) >= 1
    assert any("optional" in n.lower() for n in tl.notes)
    assert isinstance(tl.dependency_graph, dict)
    assert "waves" in tl.dependency_graph


def test_optional_marker_parsed(failed_activate_path):
    tl = parse_tasklist(failed_activate_path)
    # Task 2 has optional sub-tasks 2.7 / 2.8 marked `- [ ]* 2.7`.
    task2 = next(t for t in tl.tasks if t.id == "2")
    optional_children = [c for c in task2.children if c.optional]
    assert any(c.id == "2.7" for c in optional_children)
    assert any(c.id == "2.8" for c in optional_children)
    # Non-optional sibling is not flagged optional.
    non_opt = next(c for c in task2.children if c.id == "2.1")
    assert non_opt.optional is False


def test_open_checkbox_state(failed_activate_path):
    tl = parse_tasklist(failed_activate_path)
    # This sample uses open `- [ ]` markers (space) throughout.
    task1 = tl.tasks[0]
    assert task1.checkbox == " "


def test_walk_and_iter_tasks(not_present_path):
    tl = parse_tasklist(not_present_path)
    flattened = list(tl.iter_tasks())
    # More than just the 7 top-level tasks (includes all children).
    assert len(flattened) > 7
    # walk() on a single task yields itself first.
    first = tl.tasks[0]
    walked = list(first.walk())
    assert walked[0] is first


def test_all_text_includes_body(activated_path):
    tl = parse_tasklist(activated_path)
    task2 = tl.tasks[1]
    text = task2.all_text()
    assert task2.title in text
    assert "openapi-generator" in text.lower()


def test_missing_file_raises():
    with pytest.raises(TasklistParseError):
        parse_tasklist("/nonexistent/path/tasks.md")


def test_empty_file_raises(tmp_path):
    empty = tmp_path / "empty.md"
    empty.write_text("   \n  \n", encoding="utf-8")
    with pytest.raises(TasklistParseError):
        parse_tasklist(str(empty))


def test_malformed_dependency_graph_tolerated(tmp_path):
    md = tmp_path / "bad.md"
    md.write_text(
        "# Plan\n\n## Tasks\n\n- [ ] 1. Do thing\n\n"
        "## Task Dependency Graph\n\n```json\n{ this is not valid json }\n```\n",
        encoding="utf-8",
    )
    tl = parse_tasklist(str(md))
    # Malformed JSON → None rather than a crash.
    assert tl.dependency_graph is None
    assert len(tl.tasks) == 1


def test_absent_optional_sections_parse_fine(tmp_path):
    md = tmp_path / "minimal.md"
    md.write_text("# Minimal Plan\n\n- [ ] 1. Only task\n", encoding="utf-8")
    tl = parse_tasklist(str(md))
    assert tl.title == "Minimal Plan"
    assert tl.overview == ""
    assert tl.notes == []
    assert tl.dependency_graph is None
    assert len(tl.tasks) == 1


def test_varied_checkbox_markers(tmp_path):
    md = tmp_path / "markers.md"
    md.write_text(
        "# Markers\n\n## Tasks\n\n"
        "- [ ] 1. Open\n"
        "- [x] 2. Done\n"
        "- [-] 3. Skipped dash\n"
        "- [~] 4. Tilde\n",
        encoding="utf-8",
    )
    tl = parse_tasklist(str(md))
    marks = {t.id: t.checkbox for t in tl.tasks}
    assert marks == {"1": " ", "2": "x", "3": "-", "4": "~"}
