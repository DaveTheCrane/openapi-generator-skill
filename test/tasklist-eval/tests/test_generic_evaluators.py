"""Tests for the generic PatternSet / BinaryEvaluator / GradedEvaluator."""

from __future__ import annotations

import re

import pytest

from tasklist_eval.evaluators import (
    Area,
    BinaryEvaluator,
    GradedEvaluator,
    PatternSet,
    find_in_tasks,
)
from tasklist_eval.models import EvaluatorKind, Task, TaskList, Verdict
from tasklist_eval.parser import parse_tasklist
from tasklist_eval.registry import build_default_registry


class _Cfg:
    graded_threshold = None
    tasklist_path = ""


CFG = _Cfg()


def _tl(*tasks: tuple[str, str]) -> TaskList:
    """Build a TaskList directly from (id, title) pairs."""
    return TaskList(title="t", tasks=[Task(id=tid, title=title) for tid, title in tasks])


# --------------------------------------------------------------------------- #
# PatternSet                                                                    #
# --------------------------------------------------------------------------- #


def test_patternset_invalid_regex_names_set_and_pattern():
    with pytest.raises(ValueError, match=r"broken.*\(unclosed"):
        PatternSet("broken", ["ok", "(unclosed"])


def test_patternset_empty_patterns_rejected():
    with pytest.raises(ValueError, match="at least one pattern"):
        PatternSet("empty", [])


def test_patternset_empty_name_rejected():
    with pytest.raises(ValueError):
        PatternSet("", ["x"])


def test_patternset_precompiled_keeps_case_sensitivity():
    ps = PatternSet("delegate", [re.compile(r"\w*ApiDelegate\b")])
    assert ps.search("implement CustomersApiDelegate") == "CustomersApiDelegate"
    assert ps.search("implement customersapidelegate") is None
    # String patterns default to IGNORECASE; flags=0 makes them case-sensitive.
    assert PatternSet("ci", ["pom\\.xml"]).search("POM.XML") == "POM.XML"
    assert PatternSet("cs", ["pom\\.xml"], flags=0).search("POM.XML") is None


def test_patternset_search_returns_first_pattern_in_order():
    ps = PatternSet("s", ("beta", "alpha"))
    # "alpha" occurs earlier in the text, but "beta" is the first pattern.
    assert ps.search("alpha then beta") == "beta"
    assert ps.search("only alpha") == "alpha"
    assert ps.search("nothing") is None


def test_find_in_tasks_uses_question_mark_for_missing_id():
    tl = _tl(("1", "add pom.xml"), (None, "edit POM.xml"), ("3", "unrelated"))
    assert find_in_tasks(PatternSet("pom", ["pom\\.xml"]), tl) == [
        ("1", "pom.xml"),
        ("?", "POM.xml"),
    ]


# --------------------------------------------------------------------------- #
# BinaryEvaluator                                                               #
# --------------------------------------------------------------------------- #

A = PatternSet("set-a", ["alpha"])
B = PatternSet("set-b", ["beta", "bravo"])
BAD = PatternSet("set-bad", ["forbidden"])


def test_binary_all_required_pass():
    ev = BinaryEvaluator("x", "d", require=[A, B], summaries={"pass": "yay"})
    r = ev.evaluate(_tl(("1", "alpha"), ("2", "beta")), CFG)
    assert r.kind is EvaluatorKind.BINARY
    assert r.verdict is Verdict.PASS
    assert r.score is None
    assert r.summary == "yay"
    assert r.details["missing"] == [] and r.details["forbidden_hits"] == []


def test_binary_one_missing_uses_matching_summary_key():
    ev = BinaryEvaluator(
        "x",
        "d",
        require=[A, B],
        summaries={"missing:set-b": "no b", "missing:all": "none", "fail": "generic"},
    )
    r = ev.evaluate(_tl(("1", "alpha")), CFG)
    assert r.verdict is Verdict.FAIL
    assert r.details["missing"] == ["set-b"]
    assert r.details["sets"]["set-b"] == {"matched": False, "role": "require", "matches": []}
    assert r.summary == "no b"

    r_none = ev.evaluate(_tl(("1", "zzz")), CFG)
    assert r_none.summary == "none"
    assert r_none.evidence == ["No matches for any pattern set in any task."]


def test_binary_default_summary_names_missing_and_forbidden():
    ev = BinaryEvaluator("x", "d", require=[A, B], forbid=[BAD])
    r = ev.evaluate(_tl(("1", "alpha forbidden")), CFG)
    assert "set-b" in r.summary and "set-bad" in r.summary


def test_binary_forbid_hit_fails_even_when_required_match():
    ev = BinaryEvaluator(
        "x", "d", require=[A, B], forbid=[BAD], summaries={"pass": "p", "fail": "f"}
    )
    r = ev.evaluate(_tl(("1", "alpha beta"), ("2", "forbidden thing")), CFG)
    assert r.verdict is Verdict.FAIL
    assert r.details["missing"] == []
    assert r.details["forbidden_hits"] == ["set-bad"]
    assert r.details["sets"]["set-bad"]["role"] == "forbid"
    assert r.summary == "f"
    assert "Task 2: set-bad (forbidden) — matched 'forbidden'" in r.evidence


def test_binary_evidence_format_and_one_match_per_set_per_task():
    ev = BinaryEvaluator("x", "d", require=[A, B])
    # Task 1 matches both B patterns; only the first (in pattern order) is recorded.
    r = ev.evaluate(_tl(("1", "bravo beta alpha"), ("2", "alpha")), CFG)
    assert r.evidence == [
        "Task 1: set-a — matched 'alpha'",
        "Task 1: set-b — matched 'beta'",
        "Task 2: set-a — matched 'alpha'",
    ]
    assert r.details["sets"]["set-a"]["matches"] == [
        {"task": "1", "text": "alpha"},
        {"task": "2", "text": "alpha"},
    ]
    assert r.details["sets"]["set-b"]["matches"] == [{"task": "1", "text": "beta"}]


# --------------------------------------------------------------------------- #
# GradedEvaluator                                                               #
# --------------------------------------------------------------------------- #

GOOD = PatternSet("good", ["good"])
BADSIG = PatternSet("bad", ["bad"])


def _graded(**kw) -> GradedEvaluator:
    areas = [
        Area("red", PatternSet("red-p", ["red"]), [GOOD], [BADSIG]),
        Area("blue", PatternSet("blue-p", ["blue"]), [GOOD], [BADSIG]),
        Area("green", PatternSet("green-p", ["green"]), [GOOD], [BADSIG]),
    ]
    return GradedEvaluator("g", "d", areas=areas, **kw)


def test_graded_all_success_pass():
    r = _graded().evaluate(_tl(("1", "red good"), ("2", "blue good"), ("3", "green good")), CFG)
    assert r.kind is EvaluatorKind.GRADED
    assert r.verdict is Verdict.PASS
    assert r.score == 1.0


def test_graded_mixed_partial_and_absent_excluded():
    r = _graded().evaluate(_tl(("1", "red good"), ("2", "blue bad")), CFG)
    assert r.verdict is Verdict.PARTIAL
    assert r.score == 0.5  # green absent → excluded
    assert r.details["areas"] == {"red": "success", "blue": "failure", "green": "absent"}
    assert r.details["decided_by"] == {"red": "good", "blue": "bad", "green": None}
    assert "[green] absent — no relevant tasks found." in r.evidence
    assert "[red] success — Task 1 matched 'good' (good)" in r.evidence


def test_graded_none_success_fail():
    r = _graded().evaluate(_tl(("1", "red bad"), ("2", "blue bad")), CFG)
    assert r.verdict is Verdict.FAIL
    assert r.score == 0.0


def test_graded_no_areas_in_scope():
    r = _graded().evaluate(_tl(("1", "nothing here")), CFG)
    assert r.verdict is Verdict.FAIL
    assert r.score == 0.0
    assert r.summary == "No relevant areas found (red/blue/green)."


@pytest.mark.parametrize(
    "winner, label, decider", [("success", "success", "good"), ("failure", "failure", "bad")]
)
def test_graded_conflict_winner(winner, label, decider):
    r = _graded(conflict_winner=winner).evaluate(_tl(("1", "red bad"), ("2", "red good")), CFG)
    assert r.details["areas"]["red"] == label
    assert r.details["decided_by"]["red"] == decider


@pytest.mark.parametrize("unmatched", ["success", "failure"])
def test_graded_unmatched_present(unmatched):
    r = _graded(unmatched_present=unmatched).evaluate(_tl(("1", "red only")), CFG)
    assert r.details["areas"]["red"] == unmatched
    assert r.details["decided_by"]["red"] is None
    assert r.evidence[0] == (
        f"[red] {unmatched} — area present but no success/failure signal found."
    )


def test_graded_decided_by_first_set_hit_in_task_then_set_order():
    other = PatternSet("other-good", ["fine"])
    ev = GradedEvaluator(
        "g", "d", areas=[Area("red", PatternSet("p", ["red"]), [GOOD, other], [BADSIG])]
    )
    # Task 1 hits only other-good; it wins because tasks are scanned first.
    r = ev.evaluate(_tl(("1", "red fine"), ("2", "red good")), CFG)
    assert r.details["decided_by"]["red"] == "other-good"
    # Within one task, set order decides.
    r = ev.evaluate(_tl(("1", "red fine good")), CFG)
    assert r.details["decided_by"]["red"] == "good"


def test_graded_custom_labels_in_details_and_summary():
    r = _graded(success_label="ok", failure_label="nope").evaluate(
        _tl(("1", "red good"), ("2", "blue bad")), CFG
    )
    assert r.details["areas"] == {"red": "ok", "blue": "nope", "green": "absent"}
    assert r.summary == (
        "1/2 in-scope areas classified ok (score 0.50). ok=['red'], nope=['blue']."
    )


# --------------------------------------------------------------------------- #
# Skill-agnostic example: a brand-new evaluator in a few lines                  #
# --------------------------------------------------------------------------- #


def test_define_new_non_openapi_evaluator(tmp_path):
    uses_tdd = BinaryEvaluator(
        id="uses-tdd",
        description="PASS iff the plan writes failing tests before the implementation.",
        require=[PatternSet("red-green", [r"red[- /]green", r"failing test first"])],
        forbid=[PatternSet("tests-skipped", [r"skip (the )?tests"])],
    )

    md = tmp_path / "tdd.md"
    md.write_text(
        "# TDD Plan\n\n## Tasks\n\n"
        "- [ ] 1. Write the failing test first for the parser\n"
        "- [ ] 2. Implement the parser (red-green-refactor)\n",
        encoding="utf-8",
    )
    r = uses_tdd.evaluate(parse_tasklist(str(md)), CFG)
    assert r.verdict is Verdict.PASS
    assert r.evidence == [
        "Task 1: red-green — matched 'failing test first'",
        "Task 2: red-green — matched 'red-green'",
    ]

    registry = build_default_registry()
    registry.register(uses_tdd)
    assert "uses-tdd" in registry.ids()
