"""Tests for API key storage and masking."""

from __future__ import annotations

from pathlib import Path

from ait_core.auth.api_key_store import APIKeyStore
from ait_core.auth.token_store import TokenStore


def test_set_get_delete_key(tmp_path: Path) -> None:
    """API key should round-trip through encrypted bundle."""

    key_store = APIKeyStore(TokenStore(root_dir=tmp_path))
    key_store.set_key("xai", "secret-key-123")
    assert key_store.get_key("xai") == "secret-key-123"
    assert key_store.delete_key("xai") is True
    assert key_store.get_key("xai") is None


def test_mask_value() -> None:
    """Mask helper should expose only beginning and ending characters."""

    assert APIKeyStore.mask_value("abcdefghijk") == "abcd...hijk"
    assert APIKeyStore.mask_value("abc") == "***"
