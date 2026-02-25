"""Tests for social command helpers."""

from __future__ import annotations

import pytest
from ait_core.auth.api_key_store import APIKeyStore
from ait_core.auth.token_store import TokenStore
from ait_core.config.settings import AITSettings
from ait_core.errors import ToolsetError
from ait_social.commands import SOCIAL_PLATFORMS, get_platform_token, service_name_for_platform


def test_supported_platforms_cover_required_networks() -> None:
    """Supported platform tuple should include required social networks."""

    assert set(SOCIAL_PLATFORMS) == {"instagram", "facebook", "twitter", "linkedin", "tiktok"}


def test_service_name_mapping() -> None:
    """Service key name mapping should be stable and namespaced."""

    assert service_name_for_platform("twitter") == "social_twitter"


def test_get_platform_token_reads_encrypted_store(tmp_path) -> None:
    """Token resolver should pull keys from encrypted API key store."""

    key_store = APIKeyStore(TokenStore(root_dir=tmp_path))
    key_store.set_key("social_instagram", "insta-token")
    token = get_platform_token(AITSettings(), "instagram", key_store=key_store)
    assert token == "insta-token"


def test_get_platform_token_raises_when_missing() -> None:
    """Missing token should raise typed auth error."""

    with pytest.raises(ToolsetError):
        get_platform_token(AITSettings(), "facebook")
