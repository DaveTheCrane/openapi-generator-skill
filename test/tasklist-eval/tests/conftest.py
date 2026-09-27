"""Pytest configuration for tasklist-eval tests.

Puts ``test/tasklist-eval`` on ``sys.path`` so ``import tasklist_eval`` works
when running ``.venv/bin/pytest test/tasklist-eval/tests/`` from the project
root. Also exposes shared fixtures for the three sample tasklists.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# test/tasklist-eval (parent of this tests/ directory)
_PACKAGE_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _PACKAGE_ROOT not in sys.path:
    sys.path.insert(0, _PACKAGE_ROOT)

_SAMPLES_DIR = os.path.join(_PACKAGE_ROOT, "samples")

# Plugin evaluators live outside the package and are loaded by path.
PLUGIN_ROOT = Path(__file__).resolve().parent.parent / "evaluators"
OPENAPI_PLUGIN_DIR = PLUGIN_ROOT / "openapi-generator"


@pytest.fixture
def plugin_root() -> Path:
    return PLUGIN_ROOT


@pytest.fixture
def openapi_plugin_dir() -> Path:
    return OPENAPI_PLUGIN_DIR


@pytest.fixture
def samples_dir() -> str:
    return _SAMPLES_DIR


@pytest.fixture
def activated_path() -> str:
    return os.path.join(_SAMPLES_DIR, "skill-present-and-activated--tasks.md")


@pytest.fixture
def not_present_path() -> str:
    return os.path.join(_SAMPLES_DIR, "skill-not-present--tasks.md")


@pytest.fixture
def failed_activate_path() -> str:
    return os.path.join(_SAMPLES_DIR, "skill-present-but-failed-to-activate--tasks.md")
