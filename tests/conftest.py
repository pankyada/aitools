"""Pytest fixtures shared across test suites."""

from __future__ import annotations

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_config_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate tool config dir per test.

    Args:
        tmp_path: Pytest temporary directory.
        monkeypatch: Pytest monkeypatch fixture.

    Returns:
        None.

    Raises:
        None.
    """

    monkeypatch.setenv("AIT_CONFIG_DIR", str(tmp_path / "ai-toolset"))
