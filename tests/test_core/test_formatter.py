"""Tests for output formatter helpers."""

from __future__ import annotations

import json

from ait_core.output.formatter import command_timer, format_output, make_success_response


def test_json_output_contract() -> None:
    """Ensure JSON output includes shared envelope fields."""

    start = command_timer()
    response = make_success_response("ait-xai", "chat", {"message": "ok"}, start)
    rendered = format_output(response, "json")
    parsed = json.loads(rendered)

    assert parsed["success"] is True
    assert parsed["data"] == {"message": "ok"}
    assert parsed["metadata"]["tool"] == "ait-xai"
    assert parsed["error"] is None


def test_plain_output_contains_success() -> None:
    """Ensure plain output includes success line."""

    start = command_timer()
    response = make_success_response("ait-memory", "stats", {"count": 2}, start)
    rendered = format_output(response, "plain")
    assert "success\tTrue" in rendered
    assert "count\t2" in rendered
