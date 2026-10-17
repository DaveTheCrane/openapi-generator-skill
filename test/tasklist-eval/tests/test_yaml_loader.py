"""Tests for the YAML evaluator loader (tasklist_eval.yaml_loader)
and the YAML plugin integration in tasklist_eval.plugins.

Covers:
  - Loading binary and graded evaluators from YAML files
  - Schema validation (missing keys, wrong types, unknown kinds, etc.)
  - PatternSet flag parsing
  - Plugin discovery interleaving YAML files with Python files
  - The bundled YAML example evaluators produce the correct oracle verdicts
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from tasklist_eval.evaluators import BinaryEvaluator, GradedEvaluator
from tasklist_eval.exceptions import PluginError
from tasklist_eval.models import EvaluatorKind, Verdict
from tasklist_eval.parser import parse_tasklist
from tasklist_eval.plugins import load_plugins
from tasklist_eval.yaml_loader import load_yaml_evaluators

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

YAML_PLUGIN_DIR = (
    Path(__file__).resolve().parent.parent / "evaluators" / "openapi-generator"
)
BINARY_YAML = YAML_PLUGIN_DIR / "generator-in-pom.yaml"
GRADED_YAML = YAML_PLUGIN_DIR / "generated-code-usage.yaml"


@dataclass
class _Cfg:
    graded_threshold = None
    tasklist_path = ""


CFG = _Cfg()


def _write(path: Path, content: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return path


# ---------------------------------------------------------------------------
# Happy-path: loading the bundled YAML evaluator files
# ---------------------------------------------------------------------------


def test_load_binary_yaml_returns_binary_evaluator():
    evs = load_yaml_evaluators(BINARY_YAML)
    assert len(evs) == 1
    assert isinstance(evs[0], BinaryEvaluator)
    assert evs[0].kind is EvaluatorKind.BINARY


def test_load_binary_yaml_id():
    evs = load_yaml_evaluators(BINARY_YAML)
    assert evs[0].id == "generator-in-pom-yaml"


def test_load_binary_yaml_has_require_sets():
    evs = load_yaml_evaluators(BINARY_YAML)
    ev = evs[0]
    require_names = {ps.name for ps in ev.require}
    assert "pom-modified" in require_names
    assert "generator-mentioned" in require_names


def test_load_binary_yaml_summaries():
    evs = load_yaml_evaluators(BINARY_YAML)
    ev = evs[0]
    assert "pass" in ev.summaries
    assert "missing:generator-mentioned" in ev.summaries
    assert "missing:pom-modified" in ev.summaries
    assert "missing:all" in ev.summaries


def test_load_graded_yaml_returns_graded_evaluator():
    evs = load_yaml_evaluators(GRADED_YAML)
    assert len(evs) == 1
    assert isinstance(evs[0], GradedEvaluator)
    assert evs[0].kind is EvaluatorKind.GRADED


def test_load_graded_yaml_id():
    evs = load_yaml_evaluators(GRADED_YAML)
    assert evs[0].id == "generated-code-usage-yaml"


def test_load_graded_yaml_three_areas():
    evs = load_yaml_evaluators(GRADED_YAML)
    ev = evs[0]
    area_names = [a.name for a in ev.areas]
    assert area_names == ["server", "address-client", "item-client"]


def test_load_graded_yaml_labels_and_threshold():
    evs = load_yaml_evaluators(GRADED_YAML)
    ev = evs[0]
    assert ev.success_label == "generated"
    assert ev.failure_label == "handcoded"
    assert ev.pass_threshold == pytest.approx(0.999)


# ---------------------------------------------------------------------------
# Oracle verdicts: YAML evaluators match Python evaluators on the samples
# ---------------------------------------------------------------------------


def test_binary_yaml_activated_pass(activated_path):
    tl = parse_tasklist(activated_path)
    r = load_yaml_evaluators(BINARY_YAML)[0].evaluate(tl, CFG)
    assert r.verdict is Verdict.PASS


def test_binary_yaml_not_present_fail(not_present_path):
    tl = parse_tasklist(not_present_path)
    r = load_yaml_evaluators(BINARY_YAML)[0].evaluate(tl, CFG)
    assert r.verdict is Verdict.FAIL


def test_binary_yaml_failed_activate_fail(failed_activate_path):
    tl = parse_tasklist(failed_activate_path)
    r = load_yaml_evaluators(BINARY_YAML)[0].evaluate(tl, CFG)
    assert r.verdict is Verdict.FAIL


def test_graded_yaml_activated_full_pass(activated_path):
    tl = parse_tasklist(activated_path)
    r = load_yaml_evaluators(GRADED_YAML)[0].evaluate(tl, CFG)
    assert r.verdict is Verdict.PASS
    assert r.score == pytest.approx(1.0)


def test_graded_yaml_not_present_fail(not_present_path):
    tl = parse_tasklist(not_present_path)
    r = load_yaml_evaluators(GRADED_YAML)[0].evaluate(tl, CFG)
    assert r.verdict is Verdict.FAIL
    assert r.score == pytest.approx(0.0)


def test_graded_yaml_failed_activate_fail(failed_activate_path):
    tl = parse_tasklist(failed_activate_path)
    r = load_yaml_evaluators(GRADED_YAML)[0].evaluate(tl, CFG)
    assert r.verdict is Verdict.FAIL


# ---------------------------------------------------------------------------
# Plugin discovery: YAML files are picked up alongside Python files
# ---------------------------------------------------------------------------


def test_yaml_evaluators_discovered_by_plugin_loader(plugin_root):
    evs = load_plugins(plugin_root)
    ids = {e.id for e in evs}
    # Both Python-originated and YAML-originated ids should be present.
    assert "generator-in-pom" in ids          # Python
    assert "generator-in-pom-yaml" in ids     # YAML


def test_yaml_evaluator_gets_group_from_folder(plugin_root):
    evs = load_plugins(plugin_root)
    yaml_ev = next(e for e in evs if e.id == "generator-in-pom-yaml")
    assert yaml_ev.plugin_group == "openapi-generator"


# ---------------------------------------------------------------------------
# YAML-declared group overrides folder-inferred group
# ---------------------------------------------------------------------------


def test_explicit_group_in_yaml_overrides_folder(tmp_path):
    _write(
        tmp_path / "some-folder" / "my_eval.yaml",
        """
group: explicit-group
evaluators:
  - id: test-explicit-group-ev
    kind: binary
    description: test
    require:
      - name: sig
        patterns: ['foo']
""",
    )
    evs = load_plugins(tmp_path)
    assert evs[0].plugin_group == "explicit-group"


# ---------------------------------------------------------------------------
# Inline YAML: multiple evaluators in one file
# ---------------------------------------------------------------------------


def test_multiple_evaluators_in_one_yaml_file(tmp_path):
    _write(
        tmp_path / "multi-group" / "multi.yaml",
        """
evaluators:
  - id: test-multi-a
    kind: binary
    description: a
    require:
      - name: sig-a
        patterns: ['alpha']
  - id: test-multi-b
    kind: binary
    description: b
    require:
      - name: sig-b
        patterns: ['beta']
""",
    )
    evs = load_plugins(tmp_path)
    assert {e.id for e in evs} == {"test-multi-a", "test-multi-b"}
    assert all(e.plugin_group == "multi-group" for e in evs)


# ---------------------------------------------------------------------------
# Flags parsing
# ---------------------------------------------------------------------------


def test_pattern_set_flags_string(tmp_path):
    yaml_path = _write(
        tmp_path / "flags-group" / "flags_test.yaml",
        """
evaluators:
  - id: test-flags-ev
    kind: binary
    description: flags test
    require:
      - name: case-sensitive-sig
        patterns: ['FooBar']
        flags: []
""",
    )
    evs = load_yaml_evaluators(yaml_path)
    ps = evs[0].require[0]
    # flags=[] means no IGNORECASE, so lowercase should not match.
    assert ps.search("foobar") is None
    assert ps.search("FooBar") == "FooBar"


def test_pattern_set_flags_list(tmp_path):
    import re
    yaml_path = _write(
        tmp_path / "flist-group" / "flist_test.yaml",
        """
evaluators:
  - id: test-flist-ev
    kind: binary
    description: flags list test
    require:
      - name: ml-sig
        patterns: ['^hello']
        flags: [MULTILINE, IGNORECASE]
""",
    )
    evs = load_yaml_evaluators(yaml_path)
    ps = evs[0].require[0]
    text = "world\nHELLO there"
    assert ps.search(text) is not None


# ---------------------------------------------------------------------------
# Graded: partial-success YAML evaluator
# ---------------------------------------------------------------------------


def test_graded_yaml_partial_synthetic(tmp_path):
    yaml_path = _write(
        tmp_path / "partial-group" / "partial.yaml",
        """
evaluators:
  - id: test-partial-graded
    kind: graded
    description: partial graded test
    success_label: generated
    failure_label: handcoded
    areas:
      - name: server
        presence:
          name: server-p
          patterns: ['controller']
        success:
          - name: gen-sig
            patterns: ['ApiDelegate']
        failure:
          - name: hand-sig
            patterns: ['@RestController']
      - name: client
        presence:
          name: client-p
          patterns: ['client']
        failure:
          - name: hand-client
            patterns: ['WebClient']
""",
    )
    md = tmp_path / "partial.md"
    md.write_text(
        "# Partial\n\n"
        "- [ ] 1. Implement CustomersApiDelegate (generated)\n"
        "- [ ] 2. Create AddressClient with injected WebClient\n",
        encoding="utf-8",
    )
    evs = load_yaml_evaluators(yaml_path)
    tl = parse_tasklist(str(md))
    r = evs[0].evaluate(tl, CFG)
    assert r.verdict is Verdict.PARTIAL
    assert 0.0 < r.score < 1.0


# ---------------------------------------------------------------------------
# Schema validation errors
# ---------------------------------------------------------------------------


def _yaml_ev_file(tmp_path: Path, name: str, content: str) -> Path:
    return _write(tmp_path / name, content)


def test_missing_evaluators_key_raises(tmp_path):
    path = _yaml_ev_file(tmp_path, "bad.yaml", "group: x\n")
    with pytest.raises(PluginError, match="evaluators"):
        load_yaml_evaluators(path)


def test_evaluators_empty_list_raises(tmp_path):
    path = _yaml_ev_file(tmp_path, "bad.yaml", "evaluators: []\n")
    with pytest.raises(PluginError, match="evaluators"):
        load_yaml_evaluators(path)


def test_evaluators_not_a_list_raises(tmp_path):
    path = _yaml_ev_file(tmp_path, "bad.yaml", "evaluators: scalar\n")
    with pytest.raises(PluginError, match="evaluators"):
        load_yaml_evaluators(path)


def test_evaluator_missing_id_raises(tmp_path):
    path = _yaml_ev_file(
        tmp_path,
        "bad.yaml",
        "evaluators:\n  - kind: binary\n    require: []\n",
    )
    with pytest.raises(PluginError, match="id"):
        load_yaml_evaluators(path)


def test_evaluator_missing_kind_raises(tmp_path):
    path = _yaml_ev_file(
        tmp_path,
        "bad.yaml",
        "evaluators:\n  - id: my-ev\n",
    )
    with pytest.raises(PluginError, match="kind"):
        load_yaml_evaluators(path)


def test_evaluator_invalid_kind_raises(tmp_path):
    path = _yaml_ev_file(
        tmp_path,
        "bad.yaml",
        "evaluators:\n  - id: my-ev\n    kind: unknown\n",
    )
    with pytest.raises(PluginError, match="kind"):
        load_yaml_evaluators(path)


def test_binary_no_require_or_forbid_raises(tmp_path):
    path = _yaml_ev_file(
        tmp_path,
        "bad.yaml",
        "evaluators:\n  - id: my-ev\n    kind: binary\n",
    )
    with pytest.raises(PluginError):
        load_yaml_evaluators(path)


def test_graded_missing_areas_raises(tmp_path):
    path = _yaml_ev_file(
        tmp_path,
        "bad.yaml",
        "evaluators:\n  - id: my-ev\n    kind: graded\n",
    )
    with pytest.raises(PluginError, match="areas"):
        load_yaml_evaluators(path)


def test_graded_area_missing_presence_raises(tmp_path):
    path = _yaml_ev_file(
        tmp_path,
        "bad.yaml",
        """
evaluators:
  - id: my-ev
    kind: graded
    areas:
      - name: server
        success: []
""",
    )
    with pytest.raises(PluginError, match="presence"):
        load_yaml_evaluators(path)


def test_pattern_set_empty_patterns_raises(tmp_path):
    path = _yaml_ev_file(
        tmp_path,
        "bad.yaml",
        """
evaluators:
  - id: my-ev
    kind: binary
    require:
      - name: sig
        patterns: []
""",
    )
    with pytest.raises(PluginError):
        load_yaml_evaluators(path)


def test_pattern_set_invalid_regex_raises(tmp_path):
    path = _yaml_ev_file(
        tmp_path,
        "bad.yaml",
        """
evaluators:
  - id: my-ev
    kind: binary
    require:
      - name: sig
        patterns: ['[invalid']
""",
    )
    with pytest.raises(PluginError):
        load_yaml_evaluators(path)


def test_unknown_flag_raises(tmp_path):
    path = _yaml_ev_file(
        tmp_path,
        "bad.yaml",
        """
evaluators:
  - id: my-ev
    kind: binary
    require:
      - name: sig
        patterns: ['foo']
        flags: NOTAFLAG
""",
    )
    with pytest.raises(PluginError, match="NOTAFLAG"):
        load_yaml_evaluators(path)


def test_nonexistent_file_raises():
    with pytest.raises(PluginError, match="does not exist"):
        load_yaml_evaluators("/nonexistent/path/eval.yaml")


def test_top_level_not_mapping_raises(tmp_path):
    path = _yaml_ev_file(tmp_path, "bad.yaml", "- just a list\n")
    with pytest.raises(PluginError, match="mapping"):
        load_yaml_evaluators(path)


# ---------------------------------------------------------------------------
# Duplicate id across YAML and Python raises PluginError
# ---------------------------------------------------------------------------


def test_yaml_duplicate_id_with_python_raises(tmp_path):
    # Write a Python plugin and a YAML plugin with the same evaluator id.
    _write(
        tmp_path / "dup-group" / "dup_py.py",
        "from tasklist_eval.evaluators import BinaryEvaluator, PatternSet\n"
        'EVALUATORS = [BinaryEvaluator(id="test-dup-id", description="d", '
        'require=[PatternSet("s", ["x"])])]\n',
    )
    _write(
        tmp_path / "dup-group" / "dup_yaml.yaml",
        """
evaluators:
  - id: test-dup-id
    kind: binary
    require:
      - name: sig
        patterns: ['x']
""",
    )
    with pytest.raises(PluginError, match="duplicate"):
        load_plugins(tmp_path)
