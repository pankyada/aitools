"""HTTP retry helpers with exponential backoff and jitter."""

from __future__ import annotations

import asyncio
import random
from typing import Any

import httpx

from ait_core.errors import ErrorCode, ExitCode, ToolsetError

MAX_RETRIES = 3
BASE_DELAY = 1.0
MAX_DELAY = 30.0
RETRY_STATUS_CODES = {429, 500, 502, 503, 504}


async def request_with_retry(
    client: httpx.AsyncClient,
    method: str,
    url: str,
    **kwargs: Any,
) -> httpx.Response:
    """Run an HTTP request with retry and jitter.

    Args:
        client: Async HTTP client.
        method: HTTP method.
        url: Request URL.
        **kwargs: Forwarded request kwargs.

    Returns:
        Successful HTTP response.

    Raises:
        ToolsetError: If retries are exhausted or network failure persists.
    """

    for attempt in range(MAX_RETRIES + 1):
        try:
            response = await client.request(method, url, **kwargs)
            if response.status_code not in RETRY_STATUS_CODES:
                return response

            if attempt == MAX_RETRIES:
                return response
        except httpx.HTTPError as exc:
            if attempt == MAX_RETRIES:
                raise ToolsetError(
                    code=ErrorCode.NETWORK_ERROR,
                    message=f"HTTP request failed after retries: {exc}",
                    exit_code=ExitCode.GENERAL_ERROR,
                ) from exc

        delay = min(BASE_DELAY * (2**attempt), MAX_DELAY)
        jitter = random.uniform(0, delay * 0.1)
        await asyncio.sleep(delay + jitter)

    raise ToolsetError(
        code=ErrorCode.GENERAL_ERROR,
        message="Retry loop exited unexpectedly",
        exit_code=ExitCode.GENERAL_ERROR,
    )
