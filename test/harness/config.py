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
    return parser


def validate_timeout(timeout: int) -> None:
    """Raise ConfigError if *timeout* is outside [1, 300]."""
    if not (1 <= timeout <= 300):
        raise ConfigError(
            f"timeout must be an integer between 1 and 300 inclusive, got {timeout!r}."
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

    # --- Layer 3: SKILL_HARNESS_MODEL env var (model only) ---
    env_model = os.environ.get("SKILL_HARNESS_MODEL")
    if env_model:
        model = env_model

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

    return HarnessConfig(
        skill_path=skill_path,
        fixture_path=fixture_path,
        model=model,
        timeout_seconds=timeout_seconds,
        verbose=verbose,
    )
