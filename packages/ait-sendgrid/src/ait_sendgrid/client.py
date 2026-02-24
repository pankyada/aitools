"""SendGrid API client."""

from __future__ import annotations

from typing import Any

import httpx
from ait_core.auth.api_key_store import APIKeyStore
from ait_core.config.settings import AITSettings
from ait_core.errors import ErrorCode, ExitCode, ToolsetError
from ait_core.http.retry import request_with_retry

from ait_sendgrid.models import SendGridEmailRequest

BASE_URL = "https://api.sendgrid.com/v3"


class SendGridClient:
    """Client for SendGrid API operations.

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

        api_key = self.settings.sendgrid.api_key or self.api_key_store.get_key("sendgrid")
        if not api_key:
            raise ToolsetError(
                code=ErrorCode.AUTH_ERROR,
                message="SendGrid API key is not configured",
                exit_code=ExitCode.AUTH_ERROR,
            )
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        """Build auth headers.

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

    async def send_email(self, request: SendGridEmailRequest) -> dict[str, object]:
        """Send an email through SendGrid.

        Args:
            request: Email send payload.

        Returns:
            Payload with success details.

        Raises:
            ToolsetError: If API request fails.
        """

        personalization: dict[str, object] = {
            "to": [{"email": item} for item in request.to],
        }
        if request.cc:
            personalization["cc"] = [{"email": item} for item in request.cc]
        if request.bcc:
            personalization["bcc"] = [{"email": item} for item in request.bcc]

        contents: list[dict[str, str]] = []
        if request.text:
            contents.append({"type": "text/plain", "value": request.text})
        if request.html:
            contents.append({"type": "text/html", "value": request.html})

        body: dict[str, object] = {
            "personalizations": [personalization],
            "from": {"email": request.from_email},
            "subject": request.subject,
            "content": contents,
        }
        if request.reply_to:
            body["reply_to"] = {"email": request.reply_to}

        response = await request_with_retry(
            self.client,
            "POST",
            f"{BASE_URL}/mail/send",
            headers=self._headers(),
            json=body,
        )
        if response.status_code >= 400:
            self._raise_http_error(response)

        message_id = response.headers.get("X-Message-Id")
        return {"accepted": response.status_code == 202, "message_id": message_id}

    async def get_account(self) -> dict[str, object]:
        """Get account details for authenticated user.

        Args:
            None.

        Returns:
            Account payload.

        Raises:
            ToolsetError: If API request fails.
        """

        response = await request_with_retry(
            self.client,
            "GET",
            f"{BASE_URL}/user/account",
            headers=self._headers(),
        )
        if response.status_code >= 400:
            self._raise_http_error(response)

        payload = response.json()
        if not isinstance(payload, dict):
            return {}
        return payload

    async def list_unsubscribes(self, limit: int = 20) -> dict[str, object]:
        """List recent unsubscribes.

        Args:
            limit: Max records.

        Returns:
            Unsubscribe payload.

        Raises:
            ToolsetError: If API request fails.
        """

        response = await request_with_retry(
            self.client,
            "GET",
            f"{BASE_URL}/suppression/unsubscribes",
            headers=self._headers(),
            params={"limit": limit},
        )
        if response.status_code >= 400:
            self._raise_http_error(response)

        payload = response.json()
        if not isinstance(payload, list):
            return {"items": []}
        return {"items": payload, "count": len(payload)}

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
        if response.status_code in {401, 403}:
            code = ErrorCode.AUTH_ERROR
            exit_code = ExitCode.AUTH_ERROR
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
            message=f"SendGrid API request failed ({response.status_code})",
            exit_code=exit_code,
            details={"body": body},
        )
