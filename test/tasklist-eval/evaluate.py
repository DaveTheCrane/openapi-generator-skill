#!/usr/bin/env python3
"""CLI entry point for the tasklist evaluation framework.

Wires the components together:

    load_config()  ->  parse_tasklist()  ->  registry.select()  ->  run()  ->  report()

Usage:
    python test/tasklist-eval/evaluate.py <path/to/tasks.md>
    python test/tasklist-eval/evaluate.py <path> --report-format junit --report-file out.xml

The process exits with the reporter's return value (0 = overall PASS,
1 = overall FAIL). Configuration and parse errors abort with exit code 2 and a
descriptive message on stderr.
"""

from __future__ import annotations

import os
import sys

# Ensure the local ``tasklist_eval`` package (alongside this file) is importable
# regardless of how the script is invoked.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tasklist_eval.config import load_config
from tasklist_eval.exceptions import ConfigError, TasklistParseError
from tasklist_eval.parser import parse_tasklist
from tasklist_eval.registry import build_default_registry
from tasklist_eval.reporter import report
from tasklist_eval.runner import run


def main() -> None:
    """Load config, parse the tasklist, run evaluators, and exit with the code."""
    registry = build_default_registry()

    try:
        config = load_config(valid_evaluator_ids=registry.ids())
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        tasklist = parse_tasklist(config.tasklist_path)
    except TasklistParseError as exc:
        print(f"Tasklist parse error: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        evaluators = registry.select(config.evaluators)
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(2)

    summary = run(tasklist, evaluators, config)
    exit_code = report(summary, config)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
