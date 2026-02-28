"""Resend API client."""

from __future__ import annotations

from typing import Any

import httpx
from ait_core.auth.api_key_store import APIKeyStore
from ait_core.config.settings import AITSettings
from ait_core.errors import ErrorCode, ExitCode, ToolsetError
from ait_core.http.retry import request_with_retry

from ait_resend.models import ResendEmailRequest

BASE_URL = "https://api.resend.com"


class ResendClient:
    """Client for Resend API operations.

    Args:
        settings: Loaded settings.
        api_key_store: Optional encrypted key store.
        http_client: Optional async HTTP client.

    Returns:
        None.

    Raises:
        ToolsetError: If API key is missing.
    """

    def __init__(
        self,
        settings: AITSettings,
        api_key_store: APIKeyStore | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self.api_key_store = api_key_store or APIKeyStore()
        self.client = http_client or httpx.AsyncClient(timeout=45)

        api_key = self.settings.resend.api_key or self.api_key_store.get_key("resend")
        if not api_key:
            raise ToolsetError(
                code=ErrorCode.AUTH_ERROR,
                message="Resend API key is not configured",
                exit_code=ExitCode.AUTH_ERROR,
                recovery_hints=[
                    "Run: ait-resend auth set-key",
                    "Or set resend.api_key in settings.toml",
                    "Get your key at: https://resend.com/api-keys",
                ],
            )
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        """Build auth headers for Resend.

        Args:
            None.

        Returns:
            Header dictionary.

        Raises:
            None.
        """

        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def send_email(self, request: ResendEmailRequest) -> dict[str, object]:
        """Send an email using Resend.

        Args:
            request: Email request payload.

        Returns:
            Response payload with email id.

        Raises:
            ToolsetError: If API request fails.
        """

        body: dict[str, object] = {
            "from": request.from_email,
            "to": request.to,
            "subject": request.subject,
        }
        if request.text:
            body["text"] = request.text
        if request.html:
            body["html"] = request.html
        if request.cc:
            body["cc"] = request.cc
        if request.bcc:
            body["bcc"] = request.bcc
        if request.reply_to:
            body["reply_to"] = request.reply_to

        response = await request_with_retry(
            self.client,
            "POST",
            f"{BASE_URL}/emails",
            headers=self._headers(),
            json=body,
        )
        if response.status_code >= 400:
            self._raise_http_error(response)

        payload = response.json()
        if not isinstance(payload, dict):
            return {}
        return payload

    async def list_emails(self, limit: int = 20) -> dict[str, object]:
        """List sent emails.

        Args:
            limit: Maximum entries to return.

        Returns:
            List payload.

        Raises:
            ToolsetError: If API request fails.
        """

        response = await request_with_retry(
            self.client,
            "GET",
            f"{BASE_URL}/emails",
            headers=self._headers(),
            params={"limit": limit},
        )
        if response.status_code >= 400:
            self._raise_http_error(response)

        payload = response.json()
        if not isinstance(payload, dict):
            return {}
        return payload

    async def get_email(self, email_id: str) -> dict[str, object]:
        """Get a sent email by ID.

        Args:
            email_id: Resend email identifier.

        Returns:
            Email payload.

        Raises:
            ToolsetError: If API request fails.
        """

        response = await request_with_retry(
            self.client,
            "GET",
            f"{BASE_URL}/emails/{email_id}",
            headers=self._headers(),
        )
        if response.status_code >= 400:
            self._raise_http_error(response)

        payload = response.json()
        if not isinstance(payload, dict):
            return {}
        return payload

    def _raise_http_error(self, response: httpx.Response) -> None:
        """Raise typed error from HTTP response.

        Args:
            response: Error response.

        Returns:
            None.

        Raises:
            ToolsetError: Always.
        """

        code = ErrorCode.GENERAL_ERROR
        exit_code = ExitCode.GENERAL_ERROR
        hints: list[str] | None = None
        if response.status_code in {401, 403}:
            code = ErrorCode.AUTH_ERROR
            exit_code = ExitCode.AUTH_ERROR
            hints = [
                "Your Resend API key may be invalid or revoked",
                "Run: ait-resend auth set-key  to update it",
                "Check your keys at: https://resend.com/api-keys",
            ]
        elif response.status_code == 404:
            code = ErrorCode.NOT_FOUND
            exit_code = ExitCode.NOT_FOUND
        elif response.status_code == 429:
            code = ErrorCode.RATE_LIMITED
            exit_code = ExitCode.RATE_LIMITED

        body: Any
        try:
            body = response.json()
        except ValueError:
            body = response.text

        raise ToolsetError(
            code=code,
            message=f"Resend API request failed ({response.status_code})",
            exit_code=exit_code,
            details={"body": body},
            recovery_hints=hints,
        )
