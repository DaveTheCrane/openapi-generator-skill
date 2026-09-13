"""Config loader for the skill test harness.

Precedence (lowest → highest):
  harness.yaml config file  <  SKILL_HARNESS_MODEL env var  <  CLI arguments
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

import yaml

from .exceptions import ConfigError
from .models import HarnessConfig

_DEFAULT_MODEL = "claude-3-5-haiku-20241022"
_DEFAULT_TIMEOUT = 30
_CONFIG_FILE = "harness.yaml"
_ALLOWED_REPORT_FORMATS = ("text", "json", "junit")


def _load_file_config(cwd: str) -> dict:
    """Load harness.yaml from *cwd* if it exists; return empty dict otherwise."""
    config_path = Path(cwd) / _CONFIG_FILE
    if not config_path.exists():
        return {}
    try:
        with config_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Failed to parse {_CONFIG_FILE}: {exc}") from exc


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Run skill activation tests against an LLM judge.",
        add_help=True,
    )
    parser.add_argument(
        "--skill",
        metavar="PATH",
        help="Path to the SKILL.md file to test.",
    )
    parser.add_argument(
        "--fixture",
        metavar="PATH",
        help="Path to the YAML prompt fixture file.",
    )
    parser.add_argument(
        "--model",
        metavar="MODEL",
        help="LLM model identifier (e.g. claude-3-5-haiku-20241022).",
    )
    parser.add_argument(
        "--timeout",
        metavar="SECONDS",
        type=int,
        help="Per-prompt LLM call timeout in seconds (1–300).",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=None,
        help="Print LLM reasoning for each prompt case.",
    )
    parser.add_argument(
        "--api-base",
        metavar="URL",
        dest="api_base",
        help="Base URL for the LLM provider API (e.g. http://localhost:11434).",
    )
    parser.add_argument(
        "--report-format",
        dest="report_format",
        choices=list(_ALLOWED_REPORT_FORMATS),
        help="Output report format (text, json, or junit). Default: text.",
    )
    parser.add_argument(
        "--report-file",
        metavar="PATH",
        dest="report_file",
        help="Write the rendered report to this file instead of stdout.",
    )
    return parser


def validate_timeout(timeout: int) -> None:
    """Raise ConfigError if *timeout* is outside [1, 300]."""
    if not (1 <= timeout <= 300):
        raise ConfigError(
            f"timeout must be an integer between 1 and 300 inclusive, got {timeout!r}."
        )


def _validate_report_format(report_format: str) -> None:
    """Raise ConfigError if *report_format* is not an allowed value."""
    if report_format not in _ALLOWED_REPORT_FORMATS:
        allowed = ", ".join(_ALLOWED_REPORT_FORMATS)
        raise ConfigError(
            f"report_format must be one of [{allowed}], got {report_format!r}."
        )


def _validate_report_file(report_file: str) -> None:
    """Raise ConfigError if *report_file*'s parent directory does not exist.

    The file itself need not pre-exist; only its parent directory must exist so
    that the report can be written.
    """
    parent = Path(report_file).parent
    if not parent.exists():
        raise ConfigError(
            f"report_file parent directory does not exist: {str(parent)!r}"
        )


def _validate_readable_file(path: str, label: str) -> None:
    """Raise ConfigError if *path* does not point to a readable file."""
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"{label} path does not exist: {path!r}")
    if not p.is_file():
        raise ConfigError(f"{label} path is not a file: {path!r}")
    if not os.access(p, os.R_OK):
        raise ConfigError(f"{label} path is not readable: {path!r}")


def load_config(argv: list[str] | None = None, cwd: str | None = None) -> HarnessConfig:
    """Resolve and validate the full harness configuration.

    Parameters
    ----------
    argv:
        Argument list to parse (defaults to ``sys.argv[1:]``).
    cwd:
        Directory to search for ``harness.yaml`` (defaults to ``os.getcwd()``).

    Returns
    -------
    HarnessConfig
        Fully resolved and validated configuration.

    Raises
    ------
    ConfigError
        If any required value is missing or any validation check fails.
    """
    if cwd is None:
        cwd = os.getcwd()

    # --- Layer 1: defaults ---
    skill_path: str | None = None
    fixture_path: str | None = None
    model: str = _DEFAULT_MODEL
    timeout_seconds: int = _DEFAULT_TIMEOUT
    verbose: bool = False
    api_base: str | None = None
    extra_params: dict = {}
    report_format: str = "text"
    report_file: str | None = None

    # --- Layer 2: harness.yaml ---
    file_config = _load_file_config(cwd)
    if "skill" in file_config:
        skill_path = str(file_config["skill"])
    if "fixture" in file_config:
        fixture_path = str(file_config["fixture"])
    if "model" in file_config:
        model = str(file_config["model"])
    if "timeout" in file_config:
        timeout_seconds = int(file_config["timeout"])
    if "verbose" in file_config:
        verbose = bool(file_config["verbose"])
    if "api_base" in file_config:
        api_base = str(file_config["api_base"])
    if "report_format" in file_config:
        report_format = str(file_config["report_format"])
    if "report_file" in file_config:
        report_file = str(file_config["report_file"])
    if "extra_params" in file_config:
        raw_extra = file_config["extra_params"]
        if not isinstance(raw_extra, dict):
            raise ConfigError(
                f"extra_params must be a mapping, got {type(raw_extra).__name__}."
            )
        extra_params = dict(raw_extra)

    # --- Layer 3: env vars ---
    env_model = os.environ.get("SKILL_HARNESS_MODEL")
    if env_model:
        model = env_model
    env_api_base = os.environ.get("SKILL_HARNESS_API_BASE")
    if env_api_base:
        api_base = env_api_base
    env_report_format = os.environ.get("SKILL_HARNESS_REPORT_FORMAT")
    if env_report_format:
        report_format = env_report_format
    env_report_file = os.environ.get("SKILL_HARNESS_REPORT_FILE")
    if env_report_file:
        report_file = env_report_file

    # --- Layer 4: CLI arguments ---
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.skill is not None:
        skill_path = args.skill
    if args.fixture is not None:
        fixture_path = args.fixture
    if args.model is not None:
        model = args.model
    if args.timeout is not None:
        timeout_seconds = args.timeout
    if args.api_base is not None:
        api_base = args.api_base
    if args.report_format is not None:
        report_format = args.report_format
    if args.report_file is not None:
        report_file = args.report_file
    # argparse sets verbose to None when not supplied (due to default=None) so
    # we only override the accumulated value when the flag was explicitly passed.
    if args.verbose:
        verbose = True

    # --- Validation ---
    if not skill_path:
        raise ConfigError(
            "skill path is required. Provide --skill or set 'skill' in harness.yaml."
        )
    if not fixture_path:
        raise ConfigError(
            "fixture path is required. Provide --fixture or set 'fixture' in harness.yaml."
        )

    _validate_readable_file(skill_path, "skill")
    _validate_readable_file(fixture_path, "fixture")

    if not model:
        raise ConfigError("model must be a non-empty string.")

    validate_timeout(timeout_seconds)

    _validate_report_format(report_format)
    if report_file is not None:
        _validate_report_file(report_file)

    return HarnessConfig(
        skill_path=skill_path,
        fixture_path=fixture_path,
        model=model,
        timeout_seconds=timeout_seconds,
        verbose=verbose,
        api_base=api_base,
        extra_params=extra_params,
        report_format=report_format,
        report_file=report_file,
    )
