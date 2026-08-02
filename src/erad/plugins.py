"""
Plugin discovery for ERAD.

ERAD extensions are discovered via the ``erad.plugins`` entry-point group
(see the ``erad_plugins`` repo). Each plugin module exposes a ``register()``
function taking no arguments and returning a metadata dict with keys:
``name``, ``version``, ``description``, ``hazard_types``, ``requires``.

The discovery layer is intentionally convention-based (no abstract base
class or Protocol): any installed distribution may declare an entry point
in the ``erad.plugins`` group and ERAD will pick it up.
"""

from __future__ import annotations

import importlib.util
import sys
from functools import lru_cache
from importlib.metadata import EntryPoint, entry_points

__all__ = [
    "clear_plugin_cache",
    "discover_plugins",
    "get_plugin",
    "get_plugin_entry_point",
    "list_plugins",
    "load_plugin",
]


def _get_entry_points() -> list[EntryPoint]:
    """Return all ``erad.plugins`` entry points (works across supported Pythons)."""
    try:
        return list(entry_points(group="erad.plugins"))
    except TypeError:  # pragma: no cover - pre-3.10-style API
        return list(entry_points().get("erad.plugins", []))


def _plugin_metadata(entry_point: EntryPoint) -> dict | None:
    """Load one entry point's ``register()`` and return its metadata dict.

    Returns ``None`` (never raises) if the entry point is broken — the module
    cannot be imported, ``register`` is missing, or it raised during the call.
    """
    try:
        metadata = entry_point.load()()
    except Exception:
        return None
    if not isinstance(metadata, dict):
        return None
    return metadata


@lru_cache(maxsize=1)
def discover_plugins() -> dict[str, dict]:
    """Discover installed ERAD plugins via the ``erad.plugins`` entry-point group.

    Each plugin's ``register()`` is invoked (no arguments); the returned
    metadata dict is collected keyed by plugin ``name``. Broken entry points
    are skipped so one bad plugin never breaks discovery.

    Returns:
        A dict mapping each plugin ``name`` to its ``register()`` metadata
        dict (``name``, ``version``, ``description``, ``hazard_types``,
        ``requires``).
    """
    plugins: dict[str, dict] = {}
    for entry_point in _get_entry_points():
        metadata = _plugin_metadata(entry_point)
        if metadata is None:
            continue
        name = metadata.get("name") or entry_point.name
        plugins[name] = metadata
    return plugins


def get_plugin(name: str) -> dict | None:
    """Return the metadata dict for a single plugin, or ``None`` if unavailable.

    Args:
        name: Plugin name (e.g., ``"forefire"``).

    Returns:
        The plugin's metadata dict, or ``None`` if the plugin is not installed
        or failed to register.
    """
    return discover_plugins().get(name)


def get_plugin_entry_point(name: str) -> EntryPoint | None:
    """Return the raw entry point for a plugin name, or ``None`` if not found.

    Args:
        name: Plugin name (e.g., ``"forefire"``).

    Returns:
        The matching ``EntryPoint``, or ``None``.
    """
    for entry_point in _get_entry_points():
        if entry_point.name == name:
            return entry_point
    return None


def load_plugin(name: str):
    """Load and return the top-level module for a discovered plugin.

    Imports the plugin's entry-point module, which triggers the package
    ``__init__`` exposing the plugin's public API (config models and the
    ``run_*_scenario`` runner). Returns ``None`` if the plugin is not
    installed or its module fails to import.

    Args:
        name: Plugin name (e.g., ``"forefire"``).

    Returns:
        The imported plugin package module, or ``None`` on failure.
    """
    entry_point = get_plugin_entry_point(name)
    if entry_point is None:
        return None
    try:
        entry_point.load()
        package_name = entry_point.value.split(":")[0].split(".")[0]
        return sys.modules.get(package_name)
    except Exception:
        return None


def _engine_available(module_name: str) -> bool:
    """Return True if ``module_name`` is importable (checked via ``find_spec``)."""
    try:
        return importlib.util.find_spec(module_name) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        return False


def list_plugins() -> list[dict]:
    """Return sorted metadata for all discovered plugins.

    Each entry is the plugin's metadata dict plus an ``available`` boolean
    indicating whether every module named in ``requires`` is importable
    (i.e., the plugin's engine dependency is installed).

    Returns:
        A sorted list of plugin metadata dicts.
    """
    plugins = []
    for name, metadata in discover_plugins().items():
        entry = dict(metadata)
        entry.setdefault("name", name)
        entry["available"] = all(
            _engine_available(module_name) for module_name in metadata.get("requires", [])
        )
        plugins.append(entry)
    return sorted(plugins, key=lambda plugin: plugin.get("name", ""))


def clear_plugin_cache() -> None:
    """Clear the ``discover_plugins`` cache (mainly useful for tests)."""
    discover_plugins.cache_clear()
