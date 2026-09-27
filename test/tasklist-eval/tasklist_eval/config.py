"""Config loader for the tasklist evaluation framework.

Precedence (lowest → highest):
  tasklist-eval.yaml config file  <  environment variables  <  CLI arguments
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from .exceptions import ConfigError

_CONFIG_FILE = "tasklist-eval.yaml"
_ALLOWED_REPORT_FORMATS = ("text", "json", "junit")


@dataclass
class EvalConfig:
    """Resolved runtime configuration for an evaluation run."""

    tasklist_path: str
    report_format: str = "text"
    report_file: str | None = None
    evaluators: list[str] | None = None      # None = all registered evaluators
    graded_threshold: float | None = None    # None = graded results informational
    verbose: bool = False
    extra_params: dict = field(default_factory=dict)


def _load_file_config(cwd: str) -> dict:
    """Load tasklist-eval.yaml from *cwd* if it exists; return empty dict otherwise."""
    config_path = Path(cwd) / _CONFIG_FILE
    if not config_path.exists():
        return {}
    try:
        with config_path.open("r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError as exc:
        raise ConfigError(f"Failed to parse {_CONFIG_FILE}: {exc}") from exc


def _build_epilog(evaluator_help: str | None = None) -> str:
    """Build the help epilog: evaluators list, examples, and env vars."""
    lines: list[str] = []
    if evaluator_help:
        lines.append("Evaluators:")
        lines.append(evaluator_help)
        lines.append("")
    lines.extend(
        [
            "Examples:",
            "  python test/tasklist-eval/evaluate.py path/to/tasks.md",
            "  python test/tasklist-eval/evaluate.py path/to/tasks.md "
            "--report-format junit --report-file reports/eval.xml",
            "  python test/tasklist-eval/evaluate.py path/to/tasks.md "
            "--evaluators generator-in-pom",
            "",
            "Environment variables:",
            "  TASKLIST_EVAL_REPORT_FORMAT  overrides --report-format",
            "  TASKLIST_EVAL_REPORT_FILE    overrides --report-file",
            "  TASKLIST_EVAL_PLUGIN_DIRS    plugin folders to load "
            "(os.pathsep-separated; replaces the default)",
            "",
            "Config precedence (later wins): tasklist-eval.yaml < env < CLI.",
        ]
    )
    return "\n".join(lines)


def _build_parser(
    valid_evaluator_ids: list[str] | None = None,
    evaluator_help: str | None = None,
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Evaluate a Kiro spec-driven tasklist to assess whether a skill was "
            "applied, using signals visible in the tasklist."
        ),
        epilog=_build_epilog(evaluator_help),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )
    parser.add_argument(
        "tasklist",
        nargs="?",
        metavar="TASKLIST",
        help="Path to the tasklist markdown file to evaluate (positional).",
    )
    parser.add_argument(
        "--tasklist",
        metavar="PATH",
        dest="tasklist_opt",
        help="Path to the tasklist markdown file to evaluate.",
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
    evaluators_help = "Comma-separated list of evaluator ids to run (default: all)."
    if valid_evaluator_ids:
        evaluators_help += " Available: " + ", ".join(valid_evaluator_ids)
    parser.add_argument(
        "--evaluators",
        metavar="a,b",
        help=evaluators_help,
    )
    parser.add_argument(
        "--graded-threshold",
        metavar="FLOAT",
        dest="graded_threshold",
        type=float,
        help="If set (0..1), graded evaluators scoring below this FAIL and gate overall.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=None,
        help="Print additional evidence detail.",
    )
    return parser


def _validate_report_format(report_format: str) -> None:
    if report_format not in _ALLOWED_REPORT_FORMATS:
        allowed = ", ".join(_ALLOWED_REPORT_FORMATS)
        raise ConfigError(
            f"report_format must be one of [{allowed}], got {report_format!r}."
        )


def _validate_report_file(report_file: str) -> None:
    """Raise ConfigError if *report_file*'s parent directory does not exist."""
    parent = Path(report_file).parent
    if not parent.exists():
        raise ConfigError(
            f"report_file parent directory does not exist: {str(parent)!r}"
        )


def _validate_readable_file(path: str, label: str) -> None:
    p = Path(path)
    if not p.exists():
        raise ConfigError(f"{label} path does not exist: {path!r}")
    if not p.is_file():
        raise ConfigError(f"{label} path is not a file: {path!r}")
    if not os.access(p, os.R_OK):
        raise ConfigError(f"{label} path is not readable: {path!r}")


def _validate_graded_threshold(threshold: float) -> None:
    if not (0.0 <= threshold <= 1.0):
        raise ConfigError(
            f"graded_threshold must be within [0, 1], got {threshold!r}."
        )


def _validate_evaluators(evaluators: list[str], valid_ids: list[str]) -> None:
    unknown = [e for e in evaluators if e not in valid_ids]
    if unknown:
        valid = ", ".join(sorted(valid_ids))
        bad = ", ".join(unknown)
        raise ConfigError(
            f"unknown evaluator id(s): {bad}. Valid ids are: {valid}."
        )


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def load_config(
    argv: list[str] | None = None,
    cwd: str | None = None,
    valid_evaluator_ids: list[str] | None = None,
    evaluator_groups: dict[str, str] | None = None,
) -> EvalConfig:
    """Resolve and validate the full evaluation configuration.

    Parameters
    ----------
    argv:
        Argument list to parse (defaults to ``sys.argv[1:]``).
    cwd:
        Directory to search for ``tasklist-eval.yaml`` (defaults to ``os.getcwd()``).
    valid_evaluator_ids:
        Known evaluator ids; when provided, requested ids are validated against
        this set so unknown ids raise a descriptive :class:`ConfigError`.
    evaluator_groups:
        Optional ``id -> plugin group`` map; non-empty groups are shown next
        to each id in the ``--help`` evaluator listing.

    Raises
    ------
    ConfigError
        If any required value is missing or any validation check fails.
    """
    if cwd is None:
        cwd = os.getcwd()

    # --- Layer 1: defaults ---
    tasklist_path: str | None = None
    report_format: str = "text"
    report_file: str | None = None
    evaluators: list[str] | None = None
    graded_threshold: float | None = None
    verbose: bool = False
    extra_params: dict = {}

    # --- Layer 2: tasklist-eval.yaml ---
    file_config = _load_file_config(cwd)
    if "tasklist" in file_config:
        tasklist_path = str(file_config["tasklist"])
    if "report_format" in file_config:
        report_format = str(file_config["report_format"])
    if "report_file" in file_config:
        report_file = str(file_config["report_file"])
    if "evaluators" in file_config:
        raw_eval = file_config["evaluators"]
        if isinstance(raw_eval, str):
            evaluators = _split_csv(raw_eval)
        elif isinstance(raw_eval, list):
            evaluators = [str(e) for e in raw_eval]
        else:
            raise ConfigError(
                f"evaluators must be a list or comma string, got {type(raw_eval).__name__}."
            )
    if "graded_threshold" in file_config and file_config["graded_threshold"] is not None:
        graded_threshold = float(file_config["graded_threshold"])
    if "verbose" in file_config:
        verbose = bool(file_config["verbose"])
    if "extra_params" in file_config:
        raw_extra = file_config["extra_params"]
        if not isinstance(raw_extra, dict):
            raise ConfigError(
                f"extra_params must be a mapping, got {type(raw_extra).__name__}."
            )
        extra_params = dict(raw_extra)

    # --- Layer 3: env vars ---
    env_report_format = os.environ.get("TASKLIST_EVAL_REPORT_FORMAT")
    if env_report_format:
        report_format = env_report_format
    env_report_file = os.environ.get("TASKLIST_EVAL_REPORT_FILE")
    if env_report_file:
        report_file = env_report_file

    # --- Layer 4: CLI arguments ---
    evaluator_help = None
    if valid_evaluator_ids:
        groups = evaluator_groups or {}
        evaluator_help = "\n".join(
            f"  {eid}  ({groups[eid]})" if groups.get(eid) else f"  {eid}"
            for eid in valid_evaluator_ids
        )
    parser = _build_parser(
        valid_evaluator_ids=valid_evaluator_ids,
        evaluator_help=evaluator_help,
    )
    args = parser.parse_args(argv)

    # --tasklist takes precedence over the positional, but either may be given.
    if args.tasklist_opt is not None:
        tasklist_path = args.tasklist_opt
    elif args.tasklist is not None:
        tasklist_path = args.tasklist
    if args.report_format is not None:
        report_format = args.report_format
    if args.report_file is not None:
        report_file = args.report_file
    if args.evaluators is not None:
        evaluators = _split_csv(args.evaluators)
    if args.graded_threshold is not None:
        graded_threshold = args.graded_threshold
    if args.verbose:
        verbose = True

    # --- Validation ---
    if not tasklist_path:
        raise ConfigError(
            "tasklist path is required. Provide it positionally, via --tasklist, "
            "or set 'tasklist' in tasklist-eval.yaml."
        )
    _validate_readable_file(tasklist_path, "tasklist")

    _validate_report_format(report_format)
    if report_file is not None:
        _validate_report_file(report_file)

    if graded_threshold is not None:
        _validate_graded_threshold(graded_threshold)

    if evaluators is not None and valid_evaluator_ids is not None:
        _validate_evaluators(evaluators, valid_evaluator_ids)

    return EvalConfig(
        tasklist_path=tasklist_path,
        report_format=report_format,
        report_file=report_file,
        evaluators=evaluators,
        graded_threshold=graded_threshold,
        verbose=verbose,
        extra_params=extra_params,
    )
