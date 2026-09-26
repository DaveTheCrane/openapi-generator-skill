"""Tests for the two built-in evaluators against the oracle verdicts."""

from __future__ import annotations

from dataclasses import dataclass

from tasklist_eval.evaluators.generated_code_usage import GeneratedCodeUsageEvaluator
from tasklist_eval.evaluators.generator_in_pom import GeneratorInPomEvaluator
from tasklist_eval.models import EvaluatorKind, TaskList, Verdict
from tasklist_eval.parser import parse_tasklist


@dataclass
class _Cfg:
    graded_threshold = None
    tasklist_path = ""


CFG = _Cfg()


# --------------------------------------------------------------------------- #
# generator-in-pom (binary)                                                     #
# --------------------------------------------------------------------------- #


def test_generator_in_pom_activated_pass(activated_path):
    tl = parse_tasklist(activated_path)
    r = GeneratorInPomEvaluator().evaluate(tl, CFG)
    assert r.kind is EvaluatorKind.BINARY
    assert r.verdict is Verdict.PASS
    assert r.score is None
    assert r.details["pom_modified"] is True
    assert r.details["generator_mentioned"] is True


def test_generator_in_pom_not_present_fail(not_present_path):
    tl = parse_tasklist(not_present_path)
    r = GeneratorInPomEvaluator().evaluate(tl, CFG)
    assert r.verdict is Verdict.FAIL
    # pom is edited but the generator is never mentioned.
    assert r.details["pom_modified"] is True
    assert r.details["generator_mentioned"] is False


def test_generator_in_pom_failed_activate_fail(failed_activate_path):
    tl = parse_tasklist(failed_activate_path)
    r = GeneratorInPomEvaluator().evaluate(tl, CFG)
    assert r.verdict is Verdict.FAIL
    assert r.details["pom_modified"] is True
    assert r.details["generator_mentioned"] is False


def test_generator_in_pom_evidence_cites_tasks(activated_path):
    tl = parse_tasklist(activated_path)
    r = GeneratorInPomEvaluator().evaluate(tl, CFG)
    assert any("Task" in bullet for bullet in r.evidence)


# --------------------------------------------------------------------------- #
# generated-code-usage (graded)                                                 #
# --------------------------------------------------------------------------- #


def test_generated_code_usage_activated_full(activated_path):
    tl = parse_tasklist(activated_path)
    r = GeneratedCodeUsageEvaluator().evaluate(tl, CFG)
    assert r.kind is EvaluatorKind.GRADED
    assert r.verdict is Verdict.PASS
    assert r.score == 1.0
    areas = r.details["areas"]
    assert areas["server"] == "generated"
    assert areas["address-client"] == "generated"
    assert areas["item-client"] == "generated"


def test_generated_code_usage_not_present_zero(not_present_path):
    tl = parse_tasklist(not_present_path)
    r = GeneratedCodeUsageEvaluator().evaluate(tl, CFG)
    assert r.verdict is Verdict.FAIL
    assert r.score == 0.0
    assert all(v == "handcoded" for v in r.details["areas"].values())


def test_generated_code_usage_failed_activate_zero(failed_activate_path):
    tl = parse_tasklist(failed_activate_path)
    r = GeneratedCodeUsageEvaluator().evaluate(tl, CFG)
    assert r.verdict is Verdict.FAIL
    assert r.score == 0.0


def test_generated_code_usage_partial_synthetic(tmp_path):
    """Generated server delegate + hand-coded clients → PARTIAL, 0 < score < 1."""
    md = tmp_path / "partial.md"
    md.write_text(
        "# Partial Plan\n\n## Tasks\n\n"
        "- [ ] 1. Configure pom.xml\n"
        "  - Add openapi-generator-maven-plugin for the server\n"
        "- [ ] 2. Implement server delegate\n"
        "  - Read the generated CustomersApiDelegate from target/generated-sources\n"
        "  - Implement CustomersApiDelegateImpl\n"
        "- [ ] 3. Implement AddressServiceClient by hand\n"
        "  - Create AddressServiceClient with @Component and injected WebClient\n"
        "  - Write MockWebServer tests for the address client\n"
        "- [ ] 4. Implement ItemServiceClient by hand\n"
        "  - Create ItemServiceClient with @Component and injected WebClient\n"
        "  - Write MockWebServer tests for the item client\n",
        encoding="utf-8",
    )
    tl = parse_tasklist(str(md))
    r = GeneratedCodeUsageEvaluator().evaluate(tl, CFG)
    assert r.verdict is Verdict.PARTIAL
    assert 0.0 < r.score < 1.0
    areas = r.details["areas"]
    assert areas["server"] == "generated"
    assert areas["address-client"] == "handcoded"
    assert areas["item-client"] == "handcoded"
    # 1 of 3 areas generated → ~0.33.
    assert abs(r.score - (1 / 3)) < 1e-9


def test_generated_code_usage_no_areas(tmp_path):
    md = tmp_path / "empty-areas.md"
    md.write_text(
        "# Nothing Relevant\n\n## Tasks\n\n- [ ] 1. Set up a logging framework\n",
        encoding="utf-8",
    )
    tl = parse_tasklist(str(md))
    r = GeneratedCodeUsageEvaluator().evaluate(tl, CFG)
    assert r.verdict is Verdict.FAIL
    assert r.score == 0.0
    assert "no relevant areas" in r.summary.lower()


def test_generated_code_usage_evidence_one_per_area(activated_path):
    tl = parse_tasklist(activated_path)
    r = GeneratedCodeUsageEvaluator().evaluate(tl, CFG)
    # One evidence bullet per area.
    assert len(r.evidence) == 3
