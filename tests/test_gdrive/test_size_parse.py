"""Tests for Drive CLI size parsing helper."""

from __future__ import annotations

from ait_gdrive.cli import _parse_size


def test_parse_size_units() -> None:
    """Human readable sizes should parse to bytes."""

    assert _parse_size("1KB") == 1024
    assert _parse_size("10MB") == 10 * 1024 * 1024
