"""Tests for config precedence and validation."""

from __future__ import annotations

import pytest

from tasklist_eval.config import load_config
from tasklist_eval.exceptions import ConfigError

VALID_IDS = ["generator-in-pom", "generated-code-usage"]


def _write_tasklist(tmp_path):
    p = tmp_path / "tasks.md"
    p.write_text("# Plan\n\n- [ ] 1. Do thing\n", encoding="utf-8")
    return str(p)


def test_positional_tasklist(tmp_path):
    path = _write_tasklist(tmp_path)
    cfg = load_config(argv=[path], cwd=str(tmp_path))
    assert cfg.tasklist_path == path
    assert cfg.report_format == "text"


def test_tasklist_flag_overrides_positional(tmp_path):
    path = _write_tasklist(tmp_path)
    other = tmp_path / "other.md"
    other.write_text("# Other\n\n- [ ] 1. x\n", encoding="utf-8")
    cfg = load_config(argv=[str(other), "--tasklist", path], cwd=str(tmp_path))
    assert cfg.tasklist_path == path


def test_yaml_config_loaded(tmp_path):
    path = _write_tasklist(tmp_path)
    (tmp_path / "tasklist-eval.yaml").write_text(
        f"tasklist: {path}\nreport_format: json\n", encoding="utf-8"
    )
    cfg = load_config(argv=[], cwd=str(tmp_path))
    assert cfg.tasklist_path == path
    assert cfg.report_format == "json"


def test_env_overrides_yaml(tmp_path, monkeypatch):
    path = _write_tasklist(tmp_path)
    (tmp_path / "tasklist-eval.yaml").write_text(
        f"tasklist: {path}\nreport_format: json\n", encoding="utf-8"
    )
    monkeypatch.setenv("TASKLIST_EVAL_REPORT_FORMAT", "junit")
    cfg = load_config(argv=[], cwd=str(tmp_path))
    assert cfg.report_format == "junit"


def test_cli_overrides_env(tmp_path, monkeypatch):
    path = _write_tasklist(tmp_path)
    monkeypatch.setenv("TASKLIST_EVAL_REPORT_FORMAT", "junit")
    cfg = load_config(argv=[path, "--report-format", "json"], cwd=str(tmp_path))
    assert cfg.report_format == "json"


def test_evaluators_csv_parsed(tmp_path):
    path = _write_tasklist(tmp_path)
    cfg = load_config(
        argv=[path, "--evaluators", "generator-in-pom,generated-code-usage"],
        cwd=str(tmp_path),
        valid_evaluator_ids=VALID_IDS,
    )
    assert cfg.evaluators == ["generator-in-pom", "generated-code-usage"]


def test_graded_threshold_parsed(tmp_path):
    path = _write_tasklist(tmp_path)
    cfg = load_config(argv=[path, "--graded-threshold", "0.5"], cwd=str(tmp_path))
    assert cfg.graded_threshold == 0.5


def test_missing_tasklist_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_config(argv=[], cwd=str(tmp_path))


def test_nonexistent_tasklist_raises(tmp_path):
    with pytest.raises(ConfigError):
        load_config(argv=[str(tmp_path / "nope.md")], cwd=str(tmp_path))


def test_bad_report_format_raises(tmp_path):
    path = _write_tasklist(tmp_path)
    # argparse rejects invalid choices with SystemExit before our validator.
    with pytest.raises(SystemExit):
        load_config(argv=[path, "--report-format", "xml"], cwd=str(tmp_path))


def test_bad_report_file_parent_raises(tmp_path):
    path = _write_tasklist(tmp_path)
    with pytest.raises(ConfigError):
        load_config(
            argv=[path, "--report-file", str(tmp_path / "missing" / "out.txt")],
            cwd=str(tmp_path),
        )


def test_graded_threshold_out_of_range_raises(tmp_path):
    path = _write_tasklist(tmp_path)
    with pytest.raises(ConfigError):
        load_config(argv=[path, "--graded-threshold", "1.5"], cwd=str(tmp_path))


def test_unknown_evaluator_raises(tmp_path):
    path = _write_tasklist(tmp_path)
    with pytest.raises(ConfigError) as exc:
        load_config(
            argv=[path, "--evaluators", "does-not-exist"],
            cwd=str(tmp_path),
            valid_evaluator_ids=VALID_IDS,
        )
    # Error should list the valid ids.
    assert "generator-in-pom" in str(exc.value)
