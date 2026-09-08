#!/usr/bin/env python3
"""CLI entry point for the skill test harness.

Wires the harness components together:

    load_config()  ->  load_skill()  ->  load_fixture()  ->  run()  ->  report()

Usage:
    python test/test_skill.py --skill <path/to/SKILL.md> --fixture <path/to/fixture.yaml>

The process exits with the reporter's return value (0 = all passed,
1 = one or more failures/errors). Configuration errors, skill-load errors,
and fixture-load errors abort the run with exit code 2 and a descriptive
message on stderr.
"""

from __future__ import annotations

import os
import sys

# Ensure the harness package (located alongside this file in ``test/``) is
# importable regardless of how this script is invoked. The harness modules
# import each other via the top-level ``harness`` package name.
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from harness.config import load_config
from harness.exceptions import ConfigError, FixtureLoadError, SkillLoadError
from harness.fixture_loader import load_fixture
from harness.reporter import report
from harness.runner import run
from harness.skill_loader import load_skill


def main() -> None:
    """Load configuration, run all activation checks, and exit with the result code."""
    try:
        config = load_config()
    except ConfigError as exc:
        print(f"Configuration error: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        skill = load_skill(config.skill_path)
    except SkillLoadError as exc:
        print(f"Skill load error: {exc}", file=sys.stderr)
        sys.exit(2)

    try:
        cases = load_fixture(config.fixture_path)
    except FixtureLoadError as exc:
        print(f"Fixture load error: {exc}", file=sys.stderr)
        sys.exit(2)

    summary = run(cases, skill, config)
    exit_code = report(summary, config.verbose)
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
