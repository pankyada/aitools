"""Tests for encrypted token persistence."""

from __future__ import annotations

from pathlib import Path

from ait_core.auth.token_store import TokenStore


def test_token_roundtrip(tmp_path: Path) -> None:
    """Token bundle should persist and load."""

    store = TokenStore(root_dir=tmp_path)
    payload = {"access_token": "abc", "refresh_token": "def"}
    store.save_token_bundle("google_test", payload)

    loaded = store.load_token_bundle("google_test")
    assert loaded == payload


def test_delete_token_bundle(tmp_path: Path) -> None:
    """Deleting existing token should return true."""

    store = TokenStore(root_dir=tmp_path)
    store.save_token_bundle("google_test", {"k": "v"})
    assert store.delete_token_bundle("google_test") is True
    assert store.load_token_bundle("google_test") is None
