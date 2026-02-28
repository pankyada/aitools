"""Dynamic tool discovery via importlib.metadata entry points."""

from __future__ import annotations

from importlib.metadata import EntryPoint, entry_points
from typing import Any

import typer


def discover_tool_apps() -> list[tuple[str, typer.Typer]]:
    """Discover registered ait tool CLIs via entry point group ``ait.tools``.

    Args:
        None.

    Returns:
        List of ``(name, typer_app)`` tuples for all installed and loadable tools.

    Raises:
        None — broken plugins are silently skipped; ``ait doctor`` will flag them.
    """

    discovered: list[tuple[str, typer.Typer]] = []
    eps: list[EntryPoint] = list(entry_points(group="ait.tools"))
    for ep in sorted(eps, key=lambda e: e.name):
        try:
            app: Any = ep.load()
            if isinstance(app, typer.Typer):
                discovered.append((ep.name, app))
        except Exception:  # noqa: BLE001
            pass
    return discovered


def list_registered_tools() -> list[str]:
    """Return names of all tools registered under ``ait.tools`` entry points.

    Args:
        None.

    Returns:
        Sorted list of tool names.

    Raises:
        None.
    """

    return sorted(ep.name for ep in entry_points(group="ait.tools"))
