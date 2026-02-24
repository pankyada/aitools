"""Tests for Google Calendar scope declarations."""

from __future__ import annotations

from ait_gcal.scopes import SCOPES_EVENTS, SCOPES_FULL, SCOPES_READ


def test_scope_sets_non_empty() -> None:
    """Scope lists should be populated and full should include all."""

    assert SCOPES_READ
    assert SCOPES_EVENTS
    for scope in [*SCOPES_READ, *SCOPES_EVENTS]:
        assert scope in SCOPES_FULL
