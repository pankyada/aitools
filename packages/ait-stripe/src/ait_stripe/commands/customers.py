"""Stripe customers command handlers."""

from __future__ import annotations

from ait_core.config.settings import AITSettings

from ait_stripe.client import StripeClient


async def run_list_customers(
    settings: AITSettings,
    limit: int = 20,
    starting_after: str | None = None,
) -> dict[str, object]:
    """List Stripe customers.

    Args:
        settings: Loaded settings.
        limit: Max records.
        starting_after: Cursor for pagination.

    Returns:
        List payload.

    Raises:
        ToolsetError: If API request fails.
    """

    client = StripeClient(settings=settings)
    return await client.list_customers(limit=limit, starting_after=starting_after)


async def run_get_customer(settings: AITSettings, customer_id: str) -> dict[str, object]:
    """Get a Stripe customer by ID.

    Args:
        settings: Loaded settings.
        customer_id: Stripe customer identifier.

    Returns:
        Customer payload.

    Raises:
        ToolsetError: If API request fails.
    """

    client = StripeClient(settings=settings)
    return await client.get_customer(customer_id)
