"""Stripe API client."""

from __future__ import annotations

from typing import Any

import httpx
from ait_core.auth.api_key_store import APIKeyStore
from ait_core.config.settings import AITSettings
from ait_core.errors import ErrorCode, ExitCode, ToolsetError
from ait_core.http.retry import request_with_retry

BASE_URL = "https://api.stripe.com/v1"
DEFAULT_STRIPE_VERSION = "2024-06-20"


class StripeClient:
    """Client for Stripe API operations.

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

        api_key = self.settings.stripe.api_key or self.api_key_store.get_key("stripe")
        if not api_key:
            raise ToolsetError(
                code=ErrorCode.AUTH_ERROR,
                message="Stripe API key is not configured",
                exit_code=ExitCode.AUTH_ERROR,
                recovery_hints=[
                    "Run: ait-stripe auth set-key",
                    "Or set stripe.api_key in settings.toml",
                    "Get your key at: https://dashboard.stripe.com/apikeys",
                ],
            )
        self.api_key = api_key
        self.stripe_version = self.settings.stripe.stripe_version or DEFAULT_STRIPE_VERSION

    def _headers(self) -> dict[str, str]:
        """Build auth headers for Stripe.

        Args:
            None.

        Returns:
            Header dictionary.

        Raises:
            None.
        """

        return {
            "Authorization": f"Bearer {self.api_key}",
            "Stripe-Version": self.stripe_version,
        }

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
                "Your Stripe API key may be invalid or revoked",
                "Run: ait-stripe auth set-key  to update it",
                "Check your keys at: https://dashboard.stripe.com/apikeys",
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
            message=f"Stripe API request failed ({response.status_code})",
            exit_code=exit_code,
            details={"body": body},
            recovery_hints=hints,
        )

    async def _get(self, path: str, params: dict[str, object] | None = None) -> dict[str, object]:
        """Perform authenticated GET request.

        Args:
            path: URL path relative to BASE_URL.
            params: Optional query parameters.

        Returns:
            Parsed JSON response.

        Raises:
            ToolsetError: If request fails.
        """

        response = await request_with_retry(
            self.client,
            "GET",
            f"{BASE_URL}{path}",
            headers=self._headers(),
            params={k: v for k, v in (params or {}).items() if v is not None},
        )
        if response.status_code >= 400:
            self._raise_http_error(response)
        payload = response.json()
        if not isinstance(payload, dict):
            return {}
        return payload

    async def get_balance(self) -> dict[str, object]:
        """Retrieve account balance.

        Args:
            None.

        Returns:
            Balance payload.

        Raises:
            ToolsetError: If API request fails.
        """

        return await self._get("/balance")

    async def list_customers(
        self, limit: int = 20, starting_after: str | None = None
    ) -> dict[str, object]:
        """List Stripe customers.

        Args:
            limit: Max records.
            starting_after: Cursor for pagination.

        Returns:
            List payload.

        Raises:
            ToolsetError: If API request fails.
        """

        return await self._get("/customers", {"limit": limit, "starting_after": starting_after})

    async def get_customer(self, customer_id: str) -> dict[str, object]:
        """Get a customer by ID.

        Args:
            customer_id: Stripe customer identifier.

        Returns:
            Customer payload.

        Raises:
            ToolsetError: If API request fails.
        """

        return await self._get(f"/customers/{customer_id}")

    async def list_charges(
        self,
        limit: int = 20,
        customer: str | None = None,
        starting_after: str | None = None,
    ) -> dict[str, object]:
        """List charges.

        Args:
            limit: Max records.
            customer: Optional customer ID filter.
            starting_after: Cursor for pagination.

        Returns:
            List payload.

        Raises:
            ToolsetError: If API request fails.
        """

        return await self._get(
            "/charges",
            {"limit": limit, "customer": customer, "starting_after": starting_after},
        )

    async def get_charge(self, charge_id: str) -> dict[str, object]:
        """Get a charge by ID.

        Args:
            charge_id: Stripe charge identifier.

        Returns:
            Charge payload.

        Raises:
            ToolsetError: If API request fails.
        """

        return await self._get(f"/charges/{charge_id}")

    async def list_payment_intents(
        self,
        limit: int = 20,
        customer: str | None = None,
        starting_after: str | None = None,
    ) -> dict[str, object]:
        """List payment intents.

        Args:
            limit: Max records.
            customer: Optional customer ID filter.
            starting_after: Cursor for pagination.

        Returns:
            List payload.

        Raises:
            ToolsetError: If API request fails.
        """

        return await self._get(
            "/payment_intents",
            {"limit": limit, "customer": customer, "starting_after": starting_after},
        )

    async def get_payment_intent(self, payment_intent_id: str) -> dict[str, object]:
        """Get a payment intent by ID.

        Args:
            payment_intent_id: Stripe payment intent identifier.

        Returns:
            Payment intent payload.

        Raises:
            ToolsetError: If API request fails.
        """

        return await self._get(f"/payment_intents/{payment_intent_id}")

    async def list_subscriptions(
        self,
        limit: int = 20,
        customer: str | None = None,
        status: str | None = None,
        starting_after: str | None = None,
    ) -> dict[str, object]:
        """List subscriptions.

        Args:
            limit: Max records.
            customer: Optional customer ID filter.
            status: Optional status filter.
            starting_after: Cursor for pagination.

        Returns:
            List payload.

        Raises:
            ToolsetError: If API request fails.
        """

        return await self._get(
            "/subscriptions",
            {
                "limit": limit,
                "customer": customer,
                "status": status,
                "starting_after": starting_after,
            },
        )

    async def get_subscription(self, subscription_id: str) -> dict[str, object]:
        """Get a subscription by ID.

        Args:
            subscription_id: Stripe subscription identifier.

        Returns:
            Subscription payload.

        Raises:
            ToolsetError: If API request fails.
        """

        return await self._get(f"/subscriptions/{subscription_id}")

    async def list_invoices(
        self,
        limit: int = 20,
        customer: str | None = None,
        status: str | None = None,
        starting_after: str | None = None,
    ) -> dict[str, object]:
        """List invoices.

        Args:
            limit: Max records.
            customer: Optional customer ID filter.
            status: Optional status filter.
            starting_after: Cursor for pagination.

        Returns:
            List payload.

        Raises:
            ToolsetError: If API request fails.
        """

        return await self._get(
            "/invoices",
            {
                "limit": limit,
                "customer": customer,
                "status": status,
                "starting_after": starting_after,
            },
        )

    async def get_invoice(self, invoice_id: str) -> dict[str, object]:
        """Get an invoice by ID.

        Args:
            invoice_id: Stripe invoice identifier.

        Returns:
            Invoice payload.

        Raises:
            ToolsetError: If API request fails.
        """

        return await self._get(f"/invoices/{invoice_id}")
