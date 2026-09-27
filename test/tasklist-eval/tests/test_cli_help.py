"""Tests for the enriched CLI ``--help`` output.

The help text should make ``--evaluators`` discoverable by listing the concrete
registered evaluator ids, and should carry an epilog with example invocations
and the supported environment variables. ``-h``/``--help`` must still exit 0.
"""

from __future__ import annotations

import re

import pytest

from tasklist_eval.config import _build_parser, load_config
from tasklist_eval.registry import build_default_registry

VALID_IDS = ["generator-in-pom", "generated-code-usage"]


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


@pytest.fixture(autouse=True)
def _wide_terminal(monkeypatch):
    """Force a wide help width so argparse never hard-wraps long evaluator ids.

    Under pytest the terminal is narrow; argparse would otherwise wrap tokens
    like ``generated-code-usage`` across lines (even mid-token at hyphens),
    breaking substring assertions on the help text.
    """
    monkeypatch.setenv("COLUMNS", "200")


def _normalize(text: str) -> str:
    """Strip ANSI color codes and collapse whitespace so wrapped help compares cleanly.

    Python 3.14's argparse colorizes help output and may hard-wrap long tokens
    to terminal width; stripping styling and re-joining on whitespace makes
    substring assertions stable regardless of width or color support.
    """
    return " ".join(_ANSI_RE.sub("", text).split())


def test_help_lists_evaluator_ids_in_flag_help():
    """The --evaluators help string names the available ids."""
    parser = _build_parser(valid_evaluator_ids=VALID_IDS)
    help_text = _normalize(parser.format_help())
    assert "Available:" in help_text
    assert "generator-in-pom" in help_text
    assert "generated-code-usage" in help_text


def test_help_has_examples_and_env_sections():
    """The epilog carries Examples and Environment variables sections."""
    parser = _build_parser(valid_evaluator_ids=VALID_IDS)
    help_text = _normalize(parser.format_help())
    assert "Examples:" in help_text
    assert "Environment variables:" in help_text
    assert "TASKLIST_EVAL_REPORT_FORMAT" in help_text
    assert "TASKLIST_EVAL_REPORT_FILE" in help_text
    # Precedence pointer.
    assert "tasklist-eval.yaml" in help_text


def test_help_renders_evaluator_descriptions_when_provided():
    """When per-evaluator descriptions are threaded in, they render in the epilog."""
    descriptions = build_default_registry().descriptions()
    evaluator_help = "\n".join(
        f"  {eid} — {desc}" for eid, desc in descriptions.items()
    )
    parser = _build_parser(
        valid_evaluator_ids=list(descriptions),
        evaluator_help=evaluator_help,
    )
    help_text = _normalize(parser.format_help())
    assert "Evaluators:" in help_text
    assert "generator-in-pom — " in help_text
    assert "OpenAPI generator" in help_text


def test_build_parser_no_args_still_works():
    """All parameters are optional; a bare _build_parser() must succeed."""
    parser = _build_parser()
    help_text = _normalize(parser.format_help())
    # Generic help retained when ids are unknown.
    assert "Comma-separated list of evaluator ids to run (default: all)." in help_text
    assert "Available:" not in help_text


def test_help_flag_exits_zero():
    """-h/--help triggers SystemExit(0) via argparse."""
    parser = _build_parser(valid_evaluator_ids=VALID_IDS)
    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--help"])
    assert exc.value.code == 0

    with pytest.raises(SystemExit) as exc_short:
        parser.parse_args(["-h"])
    assert exc_short.value.code == 0


def test_load_config_help_lists_ids_and_exits_zero(tmp_path):
    """The full load_config path renders ids and exits 0 on --help."""
    with pytest.raises(SystemExit) as exc:
        load_config(argv=["--help"], cwd=str(tmp_path), valid_evaluator_ids=VALID_IDS)
    assert exc.value.code == 0


def test_registry_descriptions_maps_ids_to_text():
    """descriptions() returns an id -> non-empty description map for built-ins."""
    descriptions = build_default_registry().descriptions()
    assert set(descriptions) == set(VALID_IDS)
    assert all(descriptions[i] for i in VALID_IDS)


def test_help_mentions_plugin_dirs_env_var():
    """The epilog documents the TASKLIST_EVAL_PLUGIN_DIRS override."""
    parser = _build_parser(valid_evaluator_ids=VALID_IDS)
    help_text = _normalize(parser.format_help())
    assert "TASKLIST_EVAL_PLUGIN_DIRS" in help_text


def test_load_config_help_shows_evaluator_group(tmp_path, capsys):
    """When groups are provided, each evaluator id is listed with its group."""
    with pytest.raises(SystemExit) as exc:
        load_config(
            argv=["--help"],
            cwd=str(tmp_path),
            valid_evaluator_ids=["generator-in-pom"],
            evaluator_groups={"generator-in-pom": "openapi-generator"},
        )
    assert exc.value.code == 0
    out = _normalize(capsys.readouterr().out)
    assert "generator-in-pom (openapi-generator)" in out
