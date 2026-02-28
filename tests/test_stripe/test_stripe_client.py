"""Tests for StripeClient."""

from __future__ import annotations

import pytest
import respx
import httpx
from ait_core.config.settings import AITSettings
from ait_core.errors import ToolsetError

from ait_stripe.client import StripeClient

BASE = "https://api.stripe.com/v1"


def _settings(api_key: str = "sk_test_abc") -> AITSettings:
    s = AITSettings()
    s.stripe.api_key = api_key
    return s


# ---------------------------------------------------------------------------
# get_balance
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_get_balance_ok() -> None:
    """get_balance returns parsed JSON on 200."""

    payload = {"object": "balance", "available": []}
    respx.get(f"{BASE}/balance").mock(return_value=httpx.Response(200, json=payload))

    client = StripeClient(settings=_settings())
    result = await client.get_balance()
    assert result["object"] == "balance"


@respx.mock
@pytest.mark.asyncio
async def test_get_balance_401_raises() -> None:
    """get_balance raises ToolsetError on 401."""

    respx.get(f"{BASE}/balance").mock(
        return_value=httpx.Response(401, json={"error": {"message": "No auth"}})
    )

    with pytest.raises(ToolsetError):
        await StripeClient(settings=_settings()).get_balance()


# ---------------------------------------------------------------------------
# list_customers
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_list_customers_ok() -> None:
    """list_customers returns list payload on 200."""

    payload = {"object": "list", "data": [{"id": "cus_1"}], "has_more": False}
    respx.get(f"{BASE}/customers").mock(return_value=httpx.Response(200, json=payload))

    result = await StripeClient(settings=_settings()).list_customers(limit=5)
    assert result["object"] == "list"
    assert len(result["data"]) == 1  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# get_customer
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_get_customer_ok() -> None:
    """get_customer returns customer payload on 200."""

    payload = {"id": "cus_1", "object": "customer"}
    respx.get(f"{BASE}/customers/cus_1").mock(return_value=httpx.Response(200, json=payload))

    result = await StripeClient(settings=_settings()).get_customer("cus_1")
    assert result["id"] == "cus_1"


@respx.mock
@pytest.mark.asyncio
async def test_get_customer_404_raises() -> None:
    """get_customer raises ToolsetError on 404."""

    respx.get(f"{BASE}/customers/cus_missing").mock(
        return_value=httpx.Response(404, json={"error": {"message": "No such customer"}})
    )

    with pytest.raises(ToolsetError):
        await StripeClient(settings=_settings()).get_customer("cus_missing")


# ---------------------------------------------------------------------------
# list_charges
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_list_charges_ok() -> None:
    """list_charges returns list payload on 200."""

    payload = {"object": "list", "data": [], "has_more": False}
    respx.get(f"{BASE}/charges").mock(return_value=httpx.Response(200, json=payload))

    result = await StripeClient(settings=_settings()).list_charges(limit=10)
    assert result["object"] == "list"


# ---------------------------------------------------------------------------
# list_payment_intents
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_list_payment_intents_ok() -> None:
    """list_payment_intents returns list payload on 200."""

    payload = {"object": "list", "data": [{"id": "pi_1"}], "has_more": False}
    respx.get(f"{BASE}/payment_intents").mock(return_value=httpx.Response(200, json=payload))

    result = await StripeClient(settings=_settings()).list_payment_intents(limit=5)
    assert result["data"][0]["id"] == "pi_1"  # type: ignore[index]


# ---------------------------------------------------------------------------
# list_subscriptions
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_list_subscriptions_filters_none_params() -> None:
    """list_subscriptions omits None params from query string."""

    payload = {"object": "list", "data": [], "has_more": False}
    route = respx.get(f"{BASE}/subscriptions").mock(
        return_value=httpx.Response(200, json=payload)
    )

    await StripeClient(settings=_settings()).list_subscriptions(limit=20)
    request = route.calls.last.request
    # customer and status should not appear when None
    assert "customer" not in str(request.url)
    assert "status" not in str(request.url)


# ---------------------------------------------------------------------------
# list_invoices / get_invoice
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_list_invoices_ok() -> None:
    """list_invoices returns list payload on 200."""

    payload = {"object": "list", "data": [], "has_more": False}
    respx.get(f"{BASE}/invoices").mock(return_value=httpx.Response(200, json=payload))

    result = await StripeClient(settings=_settings()).list_invoices(limit=10)
    assert result["object"] == "list"


@respx.mock
@pytest.mark.asyncio
async def test_get_invoice_ok() -> None:
    """get_invoice returns invoice payload on 200."""

    payload = {"id": "in_1", "object": "invoice"}
    respx.get(f"{BASE}/invoices/in_1").mock(return_value=httpx.Response(200, json=payload))

    result = await StripeClient(settings=_settings()).get_invoice("in_1")
    assert result["id"] == "in_1"


# ---------------------------------------------------------------------------
# 429 rate limit
# ---------------------------------------------------------------------------


@respx.mock
@pytest.mark.asyncio
async def test_rate_limit_raises() -> None:
    """429 response raises ToolsetError."""

    respx.get(f"{BASE}/balance").mock(
        return_value=httpx.Response(429, json={"error": {"message": "Too many requests"}})
    )

    with pytest.raises(ToolsetError):
        await StripeClient(settings=_settings()).get_balance()
