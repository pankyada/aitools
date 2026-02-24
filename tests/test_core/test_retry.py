"""Tests for HTTP retry helper."""

from __future__ import annotations

import httpx
import pytest
from ait_core.errors import ToolsetError
from ait_core.http.retry import request_with_retry


@pytest.mark.asyncio
async def test_retry_until_success() -> None:
    """Request helper should retry recoverable responses."""

    attempts = {"count": 0}

    def handler(request: httpx.Request) -> httpx.Response:
        attempts["count"] += 1
        if attempts["count"] < 3:
            return httpx.Response(503, request=request)
        return httpx.Response(200, request=request, json={"ok": True})

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        response = await request_with_retry(client, "GET", "https://example.test")

    assert response.status_code == 200
    assert attempts["count"] == 3


@pytest.mark.asyncio
async def test_retry_raises_on_network_error() -> None:
    """Request helper should raise typed error after repeated network failures."""

    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ConnectError("boom", request=request)

    transport = httpx.MockTransport(handler)
    async with httpx.AsyncClient(transport=transport) as client:
        with pytest.raises(ToolsetError):
            await request_with_retry(client, "GET", "https://example.test")
