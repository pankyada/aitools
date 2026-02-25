"""Social provider interface and shared helpers."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

import httpx
from ait_core.errors import ErrorCode, ExitCode, ToolsetError
from ait_core.http.retry import request_with_retry

from ait_social.models import SocialPostRequest, SocialPostResult, SocialProfileResult


class SocialProvider(ABC):
    """Abstract provider interface for social networks."""

    platform: str

    def __init__(self, access_token: str, http_client: httpx.AsyncClient | None = None) -> None:
        self.access_token = access_token
        self.client = http_client or httpx.AsyncClient(timeout=45)

    @abstractmethod
    async def create_post(self, request: SocialPostRequest) -> SocialPostResult:
        """Create a post on the provider platform."""

    @abstractmethod
    async def get_profile(self, account_id: str | None = None) -> SocialProfileResult:
        """Get profile/account information for the provider."""

    async def _request(
        self,
        method: str,
        url: str,
        *,
        headers: dict[str, str] | None = None,
        params: dict[str, Any] | None = None,
        json: dict[str, Any] | None = None,
    ) -> httpx.Response:
        """Execute HTTP request with retry policy.

        Args:
            method: HTTP method.
            url: Full request URL.
            headers: Optional request headers.
            params: Optional query params.
            json: Optional JSON payload.

        Returns:
            HTTP response.

        Raises:
            ToolsetError: On transport failures.
        """

        return await request_with_retry(
            self.client,
            method,
            url,
            headers=headers,
            params=params,
            json=json,
        )

    def raise_for_status(self, response: httpx.Response, provider: str) -> None:
        """Raise normalized tool error for provider response failures.

        Args:
            response: HTTP response.
            provider: Provider name for message context.

        Returns:
            None.

        Raises:
            ToolsetError: Always when status is non-2xx.
        """

        if response.status_code < 400:
            return

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
            message=f"{provider} API request failed ({response.status_code})",
            exit_code=exit_code,
            details={"body": body},
        )
