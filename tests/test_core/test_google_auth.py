"""Tests for Google OAuth device flow and token refresh logic."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest
import respx
from ait_core.auth.google_auth import DEVICE_CODE_URL, TOKEN_URL, GoogleAuthClient, TokenResponse
from ait_core.auth.token_store import TokenStore
from ait_core.config.settings import AITSettings
from ait_core.errors import ToolsetError


def _settings() -> AITSettings:
    settings = AITSettings()
    settings.google.client_id = "cid"
    settings.google.client_secret = "csecret"
    return settings


@pytest.mark.asyncio
async def test_request_device_code(tmp_path: Path) -> None:
    """Device-code request should parse response payload."""

    with respx.mock(assert_all_called=True) as router:
        router.post(DEVICE_CODE_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "device_code": "dev-code",
                    "user_code": "ABCD-EFGH",
                    "verification_url": "https://google.com/device",
                    "expires_in": 1800,
                    "interval": 2,
                },
            )
        )
        client = GoogleAuthClient(settings=_settings(), token_store=TokenStore(root_dir=tmp_path))
        data = await client.request_device_code(["scope.read"])

    assert data.device_code == "dev-code"
    assert data.user_code == "ABCD-EFGH"


@pytest.mark.asyncio
async def test_poll_for_tokens_pending_then_success(tmp_path: Path) -> None:
    """Polling should continue through pending state and return token response."""

    with respx.mock(assert_all_called=True) as router:
        router.post(TOKEN_URL).mock(
            side_effect=[
                httpx.Response(400, json={"error": "authorization_pending"}),
                httpx.Response(
                    200,
                    json={
                        "access_token": "token-1",
                        "refresh_token": "refresh-1",
                        "expires_in": 3600,
                        "token_type": "Bearer",
                        "scope": "scope.read",
                    },
                ),
            ]
        )
        client = GoogleAuthClient(settings=_settings(), token_store=TokenStore(root_dir=tmp_path))
        token = await client.poll_for_tokens("dev", interval=0, expires_in=30)

    assert token.access_token == "token-1"
    assert token.refresh_token == "refresh-1"


@pytest.mark.asyncio
async def test_store_get_and_refresh_access_token(tmp_path: Path) -> None:
    """Expired stored token should refresh and return updated access token."""

    settings = _settings()
    store = TokenStore(root_dir=tmp_path)
    client = GoogleAuthClient(settings=settings, token_store=store)
    scopes = ["scope.read"]

    expired_token = TokenResponse(
        access_token="old-access",
        refresh_token="refresh",
        expires_in=1,
        token_type="Bearer",
        scope="scope.read",
    )
    client.store_token_response(scopes, expired_token)

    key = client._scope_key(scopes)
    bundle = store.load_token_bundle(key)
    assert bundle is not None
    bundle["expires_at"] = (datetime.now(tz=UTC) - timedelta(minutes=5)).isoformat()
    store.save_token_bundle(key, bundle)

    with respx.mock(assert_all_called=True) as router:
        router.post(TOKEN_URL).mock(
            return_value=httpx.Response(
                200,
                json={
                    "access_token": "new-access",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                    "scope": "scope.read",
                },
            )
        )
        access_token = await client.get_valid_access_token(scopes)

    assert access_token == "new-access"


@pytest.mark.asyncio
async def test_refresh_requires_refresh_token(tmp_path: Path) -> None:
    """Refresh should fail when no refresh token exists."""

    settings = _settings()
    store = TokenStore(root_dir=tmp_path)
    client = GoogleAuthClient(settings=settings, token_store=store)
    scopes = ["scope.read"]
    store.save_token_bundle(
        client._scope_key(scopes),
        {
            "access_token": "a",
            "scope": "scope.read",
            "token_type": "Bearer",
            "expires_at": datetime.now(tz=UTC).isoformat(),
            "scopes": scopes,
        },
    )

    with pytest.raises(ToolsetError):
        await client.refresh_access_token(scopes)


def test_logout_removes_bundle(tmp_path: Path) -> None:
    """Logout should remove the scoped token bundle."""

    settings = _settings()
    store = TokenStore(root_dir=tmp_path)
    client = GoogleAuthClient(settings=settings, token_store=store)
    scopes = ["scope.read"]
    store.save_token_bundle(client._scope_key(scopes), {"access_token": "a", "expires_at": "never"})

    assert client.logout(scopes) is True
