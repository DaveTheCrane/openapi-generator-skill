"""Evaluator plugin discovery.

Skill-specific evaluators live outside the framework package, in plugin
folders laid out as::

    <root>/
      <group>/            e.g. "openapi-generator" (hyphens allowed)
        some_module.py    exposes EVALUATORS = [SomeEvaluator(), ...]

:func:`load_plugins` scans every immediate subdirectory of *root* (sorted,
skipping names starting with ``.`` or ``_``), imports each ``*.py`` file in it
(sorted, skipping names starting with ``_``) under a synthetic module name, and
collects the module-level ``EVALUATORS`` list. A module without ``EVALUATORS``
is skipped silently (it may be a shared helper). Each collected evaluator gets
``plugin_group`` set to its folder name unless it already declares one.

Plugin folders are not Python packages, so plugin modules must use absolute
imports (``from tasklist_eval.evaluators import ...``).
"""

from __future__ import annotations

import hashlib
import importlib.util
import re
import sys
import types
from pathlib import Path
from typing import Iterable

from .evaluators.base import Evaluator
from .exceptions import PluginError

# Synthetic top-level package that all plugin modules are registered under.
PLUGIN_PACKAGE = "tasklist_eval_plugins"


def _sanitize(name: str) -> str:
    """Turn a folder/file name into a valid Python identifier segment."""
    ident = re.sub(r"\W", "_", name)
    if not ident or ident[0].isdigit():
        ident = f"_{ident}"
    return ident


def _ensure_package(name: str) -> None:
    """Register an empty synthetic package in ``sys.modules`` if missing.

    Having the parent packages present lets ``pickle``/``dataclasses`` resolve
    ``sys.modules[cls.__module__]`` for classes defined in plugin modules.
    """
    if name not in sys.modules:
        pkg = types.ModuleType(name)
        pkg.__path__ = []  # mark as a package
        sys.modules[name] = pkg


def _module_name(path: Path) -> str:
    """Return a unique synthetic module name for the plugin file *path*.

    ``tasklist_eval_plugins.<sanitized_dir>.<stem>``; if that name is already
    taken by a *different* file (e.g. two roots with the same group name), a
    short hash of the directory path is appended to the group segment.
    """
    group = _sanitize(path.parent.name)
    stem = _sanitize(path.stem)
    name = f"{PLUGIN_PACKAGE}.{group}.{stem}"
    existing = sys.modules.get(name)
    existing_file = getattr(existing, "__file__", None)
    if existing is not None and existing_file and Path(existing_file).resolve() != path:
        digest = hashlib.sha1(str(path.parent).encode("utf-8")).hexdigest()[:8]
        name = f"{PLUGIN_PACKAGE}.{group}_{digest}.{stem}"
    return name


def load_plugin_module(path: str | Path) -> types.ModuleType:
    """Import the plugin file at *path* and return the module.

    The module is registered in ``sys.modules`` under a synthetic name before
    it is executed.

    Raises
    ------
    PluginError
        If the file does not exist or fails to import.
    """
    path = Path(path).resolve()
    if not path.is_file():
        raise PluginError(f"plugin file does not exist: {str(path)!r}")

    name = _module_name(path)
    package, _, _ = name.rpartition(".")
    _ensure_package(PLUGIN_PACKAGE)
    _ensure_package(package)

    spec = importlib.util.spec_from_file_location(name, path)
    if spec is None or spec.loader is None:
        raise PluginError(f"cannot load plugin file {str(path)!r}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # noqa: BLE001 — wrap any import-time failure
        sys.modules.pop(name, None)
        raise PluginError(
            f"failed to import plugin {str(path)!r}: {type(exc).__name__}: {exc}"
        ) from exc
    return module


def _evaluators_of(module: types.ModuleType, path: Path) -> list[Evaluator]:
    """Return the validated ``EVALUATORS`` list of *module* (``[]`` if absent)."""
    if not hasattr(module, "EVALUATORS"):
        return []
    evaluators = module.EVALUATORS
    if not isinstance(evaluators, list):
        raise PluginError(
            f"{str(path)!r}: EVALUATORS must be a list of Evaluator instances, "
            f"got {type(evaluators).__name__}"
        )
    for ev in evaluators:
        if not isinstance(ev, Evaluator):
            raise PluginError(
                f"{str(path)!r}: EVALUATORS must contain only Evaluator instances, "
                f"got {type(ev).__name__}"
            )
        if not ev.id:
            raise PluginError(
                f"{str(path)!r}: evaluator {type(ev).__name__} has an empty id"
            )
    return evaluators


def _plugin_files(root: Path) -> Iterable[tuple[str, Path]]:
    """Yield ``(group, file)`` pairs in deterministic (sorted) order."""
    for group_dir in sorted(root.iterdir(), key=lambda p: p.name):
        if not group_dir.is_dir() or group_dir.name.startswith((".", "_")):
            continue
        for file in sorted(group_dir.glob("*.py"), key=lambda p: p.name):
            if file.name.startswith("_") or not file.is_file():
                continue
            yield group_dir.name, file


def _load_into(root: str | Path, seen: dict[str, Path]) -> list[Evaluator]:
    root_path = Path(root).expanduser()
    if not root_path.is_dir():
        raise PluginError(f"plugin directory does not exist: {str(root)!r}")
    root_path = root_path.resolve()

    loaded: list[Evaluator] = []
    for group, file in _plugin_files(root_path):
        module = load_plugin_module(file)
        for ev in _evaluators_of(module, file):
            if ev.id in seen:
                raise PluginError(
                    f"duplicate evaluator id {ev.id!r} defined in "
                    f"{str(seen[ev.id])!r} and {str(file)!r}"
                )
            seen[ev.id] = file
            if not getattr(ev, "plugin_group", ""):
                ev.plugin_group = group
            loaded.append(ev)
    return loaded


def load_plugins(root: str | Path) -> list[Evaluator]:
    """Discover and return every evaluator declared under plugin *root*.

    Raises
    ------
    PluginError
        If *root* does not exist, a plugin fails to import, ``EVALUATORS`` has
        the wrong type, or two plugins declare the same evaluator id.
    """
    return _load_into(root, {})


def load_plugin_dirs(roots: Iterable[str | Path]) -> list[Evaluator]:
    """Load plugins from several roots, rejecting duplicate ids across all of them."""
    seen: dict[str, Path] = {}
    evaluators: list[Evaluator] = []
    for root in roots:
        evaluators.extend(_load_into(root, seen))
    return evaluators
