"""Tests for RFC3339 normalization."""

from __future__ import annotations

import pytest
from ait_core.errors import ToolsetError
from ait_gcal.client import GCalClient


def test_normalize_rfc3339_with_z() -> None:
    """Zulu datetime should normalize and preserve UTC semantics."""

    value = GCalClient.normalize_rfc3339("2026-03-01T09:00:00Z")
    assert value.endswith("Z")


def test_normalize_rfc3339_adds_timezone() -> None:
    """Naive datetime should default to UTC."""

    value = GCalClient.normalize_rfc3339("2026-03-01T09:00:00")
    assert value.endswith("Z")


def test_normalize_rfc3339_invalid() -> None:
    """Invalid datetime should raise a typed input error."""

    with pytest.raises(ToolsetError):
        GCalClient.normalize_rfc3339("not-a-date")
