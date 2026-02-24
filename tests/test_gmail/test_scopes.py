"""Tests for Gmail scope declarations."""

from __future__ import annotations

from ait_gmail.scopes import SCOPES_FULL, SCOPES_MODIFY, SCOPES_READ, SCOPES_SEND


def test_scope_sets_non_empty() -> None:
    """Scope lists should be populated and full should include all."""

    assert SCOPES_READ
    assert SCOPES_SEND
    assert SCOPES_MODIFY
    for scope in [*SCOPES_READ, *SCOPES_SEND, *SCOPES_MODIFY]:
        assert scope in SCOPES_FULL
