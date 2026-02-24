"""Tests for xAI prompt resolution."""

from __future__ import annotations

from pathlib import Path

from ait_xai.commands.chat import resolve_prompt


def test_resolve_prompt_direct() -> None:
    """Direct prompt should be returned unchanged."""

    assert resolve_prompt(prompt="hello", prompt_file=None, use_stdin=False) == "hello"


def test_resolve_prompt_file(tmp_path: Path) -> None:
    """Prompt file should be loaded when direct prompt is absent."""

    file_path = tmp_path / "prompt.txt"
    file_path.write_text("from file", encoding="utf-8")
    assert resolve_prompt(prompt=None, prompt_file=file_path, use_stdin=False) == "from file"
