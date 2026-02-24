"""Tests for SendGrid content resolution."""

from __future__ import annotations

from pathlib import Path

import pytest
from ait_core.errors import ToolsetError
from ait_sendgrid.commands.send import resolve_content


def test_resolve_content_from_values() -> None:
    """Direct values should be returned unchanged."""

    text, html = resolve_content("hello", None, "<p>hi</p>", None)
    assert text == "hello"
    assert html == "<p>hi</p>"


def test_resolve_content_requires_input(tmp_path: Path) -> None:
    """No content should raise invalid-input error."""

    _ = tmp_path
    with pytest.raises(ToolsetError):
        resolve_content(None, None, None, None)
