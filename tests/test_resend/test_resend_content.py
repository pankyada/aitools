"""Tests for Resend content resolution."""

from __future__ import annotations

from pathlib import Path

import pytest
from ait_core.errors import ToolsetError
from ait_resend.commands.send import resolve_content


def test_resolve_content_from_files(tmp_path: Path) -> None:
    """File inputs should be loaded as message body content."""

    text_path = tmp_path / "body.txt"
    html_path = tmp_path / "body.html"
    text_path.write_text("hello", encoding="utf-8")
    html_path.write_text("<p>hello</p>", encoding="utf-8")

    text, html = resolve_content(None, text_path, None, html_path)
    assert text == "hello"
    assert html == "<p>hello</p>"


def test_resolve_content_requires_input() -> None:
    """No content should raise invalid-input error."""

    with pytest.raises(ToolsetError):
        resolve_content(None, None, None, None)
