"""Google OAuth device-code flow and token refresh helpers."""

from __future__ import annotations

import asyncio
import time
from datetime import UTC, datetime, timedelta
from hashlib import sha1
from typing import Any

import httpx
from pydantic import BaseModel

from ait_core.auth.token_store import TokenStore
from ait_core.config.settings import AITSettings
from ait_core.errors import ErrorCode, ExitCode, ToolsetError

DEVICE_CODE_URL = "https://oauth2.googleapis.com/device/code"
TOKEN_URL = "https://oauth2.googleapis.com/token"


class DeviceCodeResponse(BaseModel):
    """Response payload from Google device-code endpoint."""

    device_code: str
    user_code: str
    verification_url: str
    expires_in: int
    interval: int = 5


class TokenResponse(BaseModel):
    """Response payload from Google OAuth token endpoint."""

    access_token: str
    expires_in: int
    token_type: str = "Bearer"
    scope: str = ""
    refresh_token: str | None = None


class GoogleAuthClient:
    """Google auth client supporting device flow and refresh flow.

    Args:
        settings: Global settings with Google OAuth credentials.
        token_store: Optional token storage backend.
        http_client: Optional async HTTP client.

    Returns:
        None.

    Raises:
        ToolsetError: If Google client credentials are missing.
    """

    def __init__(
        self,
        settings: AITSettings,
        token_store: TokenStore | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self.token_store = token_store or TokenStore()
        self.client = http_client or httpx.AsyncClient(timeout=30)

        if not self.settings.google.client_id or not self.settings.google.client_secret:
            raise ToolsetError(
                code=ErrorCode.AUTH_ERROR,
                message="Google client_id/client_secret are not configured",
                exit_code=ExitCode.AUTH_ERROR,
                recovery_hints=[
                    "Set google.client_id and google.client_secret in settings.toml",
                    "Create OAuth credentials at: https://console.cloud.google.com/apis/credentials",
                    "Choose 'Desktop app' as the application type when creating credentials",
                ],
            )

    async def request_device_code(self, scopes: list[str]) -> DeviceCodeResponse:
        """Start device-code flow by requesting a user verification code.

        Args:
            scopes: OAuth scopes to request.

        Returns:
            Device code response payload.

        Raises:
            ToolsetError: If request fails or response is invalid.
        """

        payload = {
            "client_id": self.settings.google.client_id,
            "scope": " ".join(scopes),
        }
        try:
            response = await self.client.post(DEVICE_CODE_URL, data=payload)
            response.raise_for_status()
            return DeviceCodeResponse.model_validate(response.json())
        except httpx.HTTPStatusError as exc:
            raise ToolsetError(
                code=ErrorCode.AUTH_ERROR,
                message=f"Google device-code request failed: {exc.response.text}",
                exit_code=ExitCode.AUTH_ERROR,
                recovery_hints=[
                    "Verify your google.client_id is correct in settings.toml",
                    "Ensure your OAuth app is enabled at: https://console.cloud.google.com/apis/credentials",
                ],
            ) from exc
        except httpx.HTTPError as exc:
            raise ToolsetError(
                code=ErrorCode.NETWORK_ERROR,
                message=f"Network error requesting device code: {exc}",
                exit_code=ExitCode.GENERAL_ERROR,
                recovery_hints=[
                    "Check your internet connection",
                    "Google OAuth endpoints may be temporarily unavailable — try again shortly",
                ],
            ) from exc

    def _scope_key(self, scopes: list[str]) -> str:
        """Build stable token bundle key for a scope set.

        Args:
            scopes: OAuth scope list.

        Returns:
            Stable bundle key string.

        Raises:
            None.
        """

        normalized = " ".join(sorted(scopes)).encode("utf-8")
        digest = sha1(normalized, usedforsecurity=False).hexdigest()[:12]
        return f"google_{digest}"

    async def poll_for_tokens(
        self, device_code: str, interval: int, expires_in: int
    ) -> TokenResponse:
        """Poll token endpoint until auth is completed or timeout reached.

        Args:
            device_code: Device code from initial request.
            interval: Poll interval from Google.
            expires_in: Device code lifetime in seconds.

        Returns:
            Token response on successful auth.

        Raises:
            ToolsetError: On timeout, denial, or token endpoint failure.
        """

        deadline = time.monotonic() + expires_in
        current_interval = max(interval, 1)

        while time.monotonic() < deadline:
            payload = {
                "client_id": self.settings.google.client_id,
                "client_secret": self.settings.google.client_secret,
                "device_code": device_code,
                "grant_type": "urn:ietf:params:oauth:grant-type:device_code",
            }
            response = await self.client.post(TOKEN_URL, data=payload)

            if response.status_code == 200:
                return TokenResponse.model_validate(response.json())

            data = response.json()
            error_value = data.get("error", "")
            if error_value == "authorization_pending":
                await asyncio.sleep(current_interval)
                continue
            if error_value == "slow_down":
                current_interval += 2
                await asyncio.sleep(current_interval)
                continue
            if error_value == "access_denied":
                raise ToolsetError(
                    code=ErrorCode.AUTH_ERROR,
                    message="Google authorization was denied by the user",
                    exit_code=ExitCode.AUTH_ERROR,
                    recovery_hints=[
                        "Re-run the login command and click 'Allow' when prompted in the browser",
                        "Make sure you are signing in with the correct Google account",
                    ],
                )
            if error_value == "expired_token":
                raise ToolsetError(
                    code=ErrorCode.AUTH_EXPIRED,
                    message="Google device code expired before authorization completed",
                    exit_code=ExitCode.AUTH_ERROR,
                    recovery_hints=[
                        "Re-run the login command and complete authorization in the browser promptly",
                        "You have a limited window after the code is shown to approve the request",
                    ],
                )

            raise ToolsetError(
                code=ErrorCode.AUTH_ERROR,
                message=f"Google token polling failed: {data}",
                exit_code=ExitCode.AUTH_ERROR,
                recovery_hints=[
                    "Re-run the login command to start a new authorization flow",
                    "Verify your OAuth app configuration at: https://console.cloud.google.com/apis/credentials",
                ],
            )

        raise ToolsetError(
            code=ErrorCode.AUTH_EXPIRED,
            message="Timed out waiting for Google device authorization",
            exit_code=ExitCode.AUTH_ERROR,
            recovery_hints=[
                "Re-run the login command and approve it in the browser more quickly",
                "The device code window is limited — complete authorization within the time shown",
            ],
        )

    async def login_device_flow(self, scopes: list[str]) -> DeviceCodeResponse:
        """Run device-code login and store resulting token bundle.

        Args:
            scopes: OAuth scopes required for the tool command set.

        Returns:
            Initial device-code response for display purposes.

        Raises:
            ToolsetError: If authorization fails.
        """

        device = await self.request_device_code(scopes)
        token = await self.poll_for_tokens(
            device_code=device.device_code,
            interval=device.interval,
            expires_in=device.expires_in,
        )
        self.store_token_response(scopes=scopes, token=token)
        return device

    def store_token_response(self, scopes: list[str], token: TokenResponse) -> None:
        """Persist token response for a scope set.

        Args:
            scopes: OAuth scopes associated with this token.
            token: Token response payload to store.

        Returns:
            None.

        Raises:
            OSError: If token persistence fails.
        """

        expires_at = datetime.now(tz=UTC) + timedelta(seconds=token.expires_in)
        bundle: dict[str, Any] = {
            "access_token": token.access_token,
            "refresh_token": token.refresh_token,
            "scope": token.scope,
            "token_type": token.token_type,
            "expires_at": expires_at.isoformat(),
            "scopes": scopes,
        }
        self.token_store.save_token_bundle(self._scope_key(scopes), bundle)

    async def refresh_access_token(self, scopes: list[str]) -> dict[str, Any]:
        """Refresh and persist access token for an existing scope-set bundle.

        Args:
            scopes: Scope list selecting the token bundle.

        Returns:
            Updated token bundle.

        Raises:
            ToolsetError: If no refresh token exists or refresh fails.
        """

        key = self._scope_key(scopes)
        bundle = self.token_store.load_token_bundle(key)
        if bundle is None:
            raise ToolsetError(
                code=ErrorCode.AUTH_ERROR,
                message="No stored Google token for requested scopes",
                exit_code=ExitCode.AUTH_ERROR,
                recovery_hints=[
                    "Run the login command for this tool to authorize your Google account",
                    "Example: ait-gmail auth login",
                ],
            )

        refresh_token = bundle.get("refresh_token")
        if not isinstance(refresh_token, str) or not refresh_token:
            raise ToolsetError(
                code=ErrorCode.AUTH_EXPIRED,
                message="Stored Google token does not include a refresh token",
                exit_code=ExitCode.AUTH_ERROR,
                recovery_hints=[
                    "Re-run the login command to obtain a fresh token with offline access",
                    "Example: ait-gmail auth login  (ensure offline_access scope is requested)",
                ],
            )

        payload = {
            "client_id": self.settings.google.client_id,
            "client_secret": self.settings.google.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            response = await self.client.post(TOKEN_URL, data=payload)
            response.raise_for_status()
        except httpx.HTTPStatusError as exc:
            raise ToolsetError(
                code=ErrorCode.AUTH_EXPIRED,
                message=f"Google token refresh failed: {exc.response.text}",
                exit_code=ExitCode.AUTH_ERROR,
                recovery_hints=[
                    "Re-run the login command to re-authorize your Google account",
                    "Check that your OAuth app is still enabled at: https://console.cloud.google.com/apis/credentials",
                    "Revoke and re-grant access at: https://myaccount.google.com/permissions",
                ],
            ) from exc

        updated = response.json()
        expires_at = datetime.now(tz=UTC) + timedelta(seconds=int(updated["expires_in"]))
        bundle["access_token"] = updated["access_token"]
        bundle["expires_at"] = expires_at.isoformat()
        self.token_store.save_token_bundle(key, bundle)
        return bundle

    async def get_valid_access_token(self, scopes: list[str]) -> str:
        """Return a valid access token, refreshing when needed.

        Args:
            scopes: Scope-set key to retrieve.

        Returns:
            Access token string.

        Raises:
            ToolsetError: If token is missing or invalid.
        """

        key = self._scope_key(scopes)
        bundle = self.token_store.load_token_bundle(key)
        if bundle is None:
            raise ToolsetError(
                code=ErrorCode.AUTH_ERROR,
                message="Google auth not configured for requested scopes",
                exit_code=ExitCode.AUTH_ERROR,
                recovery_hints=[
                    "Run the login command for this tool to authorize your Google account",
                    "Example: ait-gmail auth login",
                ],
            )

        access_token = bundle.get("access_token")
        expires_at_raw = bundle.get("expires_at")
        if not isinstance(access_token, str) or not isinstance(expires_at_raw, str):
            raise ToolsetError(
                code=ErrorCode.AUTH_EXPIRED,
                message="Stored Google token payload is invalid",
                exit_code=ExitCode.AUTH_ERROR,
                recovery_hints=[
                    "Log out and log back in to replace the corrupted token",
                    "Example: ait-gmail auth logout  then  ait-gmail auth login",
                ],
            )

        expires_at = datetime.fromisoformat(expires_at_raw)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)

        if datetime.now(tz=UTC) + timedelta(seconds=60) >= expires_at:
            refreshed = await self.refresh_access_token(scopes)
            refreshed_token = refreshed.get("access_token")
            if not isinstance(refreshed_token, str):
                raise ToolsetError(
                    code=ErrorCode.AUTH_EXPIRED,
                    message="Google token refresh returned invalid access token",
                    exit_code=ExitCode.AUTH_ERROR,
                    recovery_hints=[
                        "Log out and log back in to obtain a clean token",
                        "Example: ait-gmail auth logout  then  ait-gmail auth login",
                    ],
                )
            return refreshed_token

        return access_token

    def logout(self, scopes: list[str]) -> bool:
        """Delete token bundle for requested scope set.

        Args:
            scopes: Scope list selecting stored token bundle.

        Returns:
            True when token bundle existed and was removed.

        Raises:
            OSError: If storage delete fails.
        """

        return self.token_store.delete_token_bundle(self._scope_key(scopes))
