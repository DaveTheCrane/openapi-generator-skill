"""Tests for evaluator plugin discovery (tasklist_eval.plugins) and the
plugin-backed default registry (tasklist_eval.registry).

Every test uses a unique group directory, file name and evaluator id, because
plugin modules are cached in ``sys.modules`` under names derived from them.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tasklist_eval.exceptions import PluginError
from tasklist_eval.plugins import load_plugin_dirs, load_plugins
from tasklist_eval.registry import (
    DEFAULT_PLUGIN_DIR,
    PLUGIN_DIRS_ENV,
    build_default_registry,
)

OPENAPI_IDS = {"generator-in-pom", "generated-code-usage"}


def _evaluator_src(*ids: str) -> str:
    items = ", ".join(
        f'BinaryEvaluator(id="{i}", description="d", require=[PatternSet("s", ["x"])])'
        for i in ids
    )
    return (
        "from tasklist_eval.evaluators import BinaryEvaluator, PatternSet\n"
        f"EVALUATORS = [{items}]\n"
    )


def _write(root: Path, group: str, filename: str, source: str) -> Path:
    group_dir = root / group
    group_dir.mkdir(parents=True, exist_ok=True)
    path = group_dir / filename
    path.write_text(source, encoding="utf-8")
    return path


def test_default_registry_has_openapi_evaluators(monkeypatch):
    monkeypatch.delenv(PLUGIN_DIRS_ENV, raising=False)
    registry = build_default_registry()
    assert set(registry.ids()) == OPENAPI_IDS
    assert registry.groups() == {i: "openapi-generator" for i in OPENAPI_IDS}


def test_hyphenated_group_dir_loads(tmp_path):
    _write(tmp_path, "my-hyphen-skill", "hyphen_plugin.py",
           _evaluator_src("test-hyphen-ev"))
    evs = load_plugins(tmp_path)
    assert [e.id for e in evs] == ["test-hyphen-ev"]
    assert evs[0].plugin_group == "my-hyphen-skill"


def test_module_without_evaluators_is_skipped(tmp_path):
    _write(tmp_path, "noevals-group", "noevals_helper.py", "HELPER = 1\n")
    assert load_plugins(tmp_path) == []


def test_evaluators_not_a_list_raises(tmp_path):
    _write(tmp_path, "badtype-group", "badtype_plugin.py",
           'EVALUATORS = "not a list"\n')
    with pytest.raises(PluginError):
        load_plugins(tmp_path)


def test_evaluators_with_non_evaluator_raises(tmp_path):
    _write(tmp_path, "baditem-group", "baditem_plugin.py",
           "EVALUATORS = [object()]\n")
    with pytest.raises(PluginError):
        load_plugins(tmp_path)


def test_import_failure_raises_with_filename(tmp_path):
    _write(tmp_path, "boom-group", "boom_plugin.py", 'raise RuntimeError("boom")\n')
    with pytest.raises(PluginError) as exc_info:
        load_plugins(tmp_path)
    assert "boom_plugin.py" in str(exc_info.value)


def test_duplicate_id_across_files_raises(tmp_path):
    _write(tmp_path, "dup-group", "dup_a.py", _evaluator_src("test-dup-ev"))
    _write(tmp_path, "dup-group", "dup_b.py", _evaluator_src("test-dup-ev"))
    with pytest.raises(PluginError, match="duplicate"):
        load_plugins(tmp_path)


def test_nonexistent_root_raises(tmp_path):
    with pytest.raises(PluginError):
        load_plugins(tmp_path / "does-not-exist")


def test_private_files_and_hidden_groups_are_ignored(tmp_path):
    _write(tmp_path, "visible-group", "_private_plugin.py",
           _evaluator_src("test-private-file-ev"))
    _write(tmp_path, ".hidden", "dot_hidden_plugin.py",
           _evaluator_src("test-dot-hidden-ev"))
    _write(tmp_path, "_hidden", "under_hidden_plugin.py",
           _evaluator_src("test-under-hidden-ev"))
    _write(tmp_path, "visible-group", "visible_plugin.py",
           _evaluator_src("test-visible-ev"))
    assert [e.id for e in load_plugins(tmp_path)] == ["test-visible-ev"]


def test_env_var_replaces_default_plugin_dir(tmp_path, monkeypatch):
    _write(tmp_path, "env-group", "env_plugin.py", _evaluator_src("test-env-ev"))
    monkeypatch.setenv(PLUGIN_DIRS_ENV, str(tmp_path))
    registry = build_default_registry()
    assert set(registry.ids()) == {"test-env-ev"}
    assert not OPENAPI_IDS & set(registry.ids())


def test_load_plugin_dirs_combines_roots(tmp_path):
    _write(tmp_path, "my-skill", "uses_tdd_plugin.py",
           _evaluator_src("test-uses-tdd-ev"))
    evs = load_plugin_dirs([DEFAULT_PLUGIN_DIR, tmp_path])
    assert len(evs) == 3
    groups = sorted(e.plugin_group for e in evs)
    assert groups == ["my-skill", "openapi-generator", "openapi-generator"]
    assert {e.id for e in evs} == OPENAPI_IDS | {"test-uses-tdd-ev"}
