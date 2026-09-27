"""Evaluator registry.

A small id → evaluator-instance registry. The runner asks the registry for the
active evaluator set (all registered by default), or a subset selected by id via
the ``--evaluators`` config option.

The default registry is populated from plugin folders (see
:mod:`tasklist_eval.plugins`): by default ``<test/tasklist-eval>/evaluators``,
overridable via the ``TASKLIST_EVAL_PLUGIN_DIRS`` environment variable
(``os.pathsep``-separated). The registry is built before argparse runs, which
is why the override is environment-only. Evaluators can also be added
programmatically by calling :meth:`EvaluatorRegistry.register`.
"""

from __future__ import annotations

import os
from pathlib import Path

from .evaluators.base import Evaluator
from .exceptions import ConfigError
from .plugins import load_plugin_dirs

#: Bundled plugin root: ``test/tasklist-eval/evaluators`` (sibling of the package).
DEFAULT_PLUGIN_DIR = Path(__file__).resolve().parent.parent / "evaluators"

#: Environment variable overriding the plugin roots (``os.pathsep``-separated).
PLUGIN_DIRS_ENV = "TASKLIST_EVAL_PLUGIN_DIRS"


class EvaluatorRegistry:
    """Maps evaluator ids to their instances."""

    def __init__(self) -> None:
        self._evaluators: dict[str, Evaluator] = {}

    def register(self, evaluator: Evaluator) -> None:
        """Register *evaluator* under its ``id``."""
        if not evaluator.id:
            raise ValueError("evaluator must define a non-empty id")
        self._evaluators[evaluator.id] = evaluator

    def ids(self) -> list[str]:
        """Return all registered evaluator ids."""
        return list(self._evaluators.keys())

    def descriptions(self) -> dict[str, str]:
        """Return an ``id -> description`` map for every registered evaluator.

        Evaluators that do not define a ``description`` map to an empty string.
        """
        return {
            eid: getattr(ev, "description", "") or ""
            for eid, ev in self._evaluators.items()
        }

    def groups(self) -> dict[str, str]:
        """Return an ``id -> plugin_group`` map (empty string when ungrouped)."""
        return {
            eid: getattr(ev, "plugin_group", "") or ""
            for eid, ev in self._evaluators.items()
        }

    def get_all(self) -> list[Evaluator]:
        """Return every registered evaluator instance."""
        return list(self._evaluators.values())

    def get(self, ids: list[str]) -> list[Evaluator]:
        """Return the evaluators for *ids*, in the requested order.

        Raises
        ------
        ConfigError
            If any requested id is not registered.
        """
        unknown = [i for i in ids if i not in self._evaluators]
        if unknown:
            valid = ", ".join(sorted(self._evaluators))
            bad = ", ".join(unknown)
            raise ConfigError(
                f"unknown evaluator id(s): {bad}. Valid ids are: {valid}."
            )
        return [self._evaluators[i] for i in ids]

    def select(self, ids: list[str] | None) -> list[Evaluator]:
        """Return the selected evaluators, or all when *ids* is None."""
        if ids is None:
            return self.get_all()
        return self.get(ids)


def _plugin_dirs_from_env() -> list[str] | None:
    """Return the ``TASKLIST_EVAL_PLUGIN_DIRS`` entries, or None when unset/blank."""
    raw = os.environ.get(PLUGIN_DIRS_ENV, "")
    dirs = [d for d in raw.split(os.pathsep) if d.strip()]
    return dirs or None


def build_default_registry(plugin_dirs: list[str] | None = None) -> EvaluatorRegistry:
    """Return a registry populated with every evaluator found in the plugin dirs.

    When *plugin_dirs* is None, ``TASKLIST_EVAL_PLUGIN_DIRS`` is used if set
    (it replaces the default), otherwise :data:`DEFAULT_PLUGIN_DIR`.

    Raises
    ------
    PluginError
        If a plugin directory is missing or a plugin cannot be loaded.
    """
    if plugin_dirs is None:
        plugin_dirs = _plugin_dirs_from_env() or [str(DEFAULT_PLUGIN_DIR)]
    registry = EvaluatorRegistry()
    for evaluator in load_plugin_dirs(plugin_dirs):
        registry.register(evaluator)
    return registry
