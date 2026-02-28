"""Stripe subscriptions command handlers."""

from __future__ import annotations

from ait_core.config.settings import AITSettings

from ait_stripe.client import StripeClient


async def run_list_subscriptions(
    settings: AITSettings,
    limit: int = 20,
    customer: str | None = None,
    status: str | None = None,
    starting_after: str | None = None,
) -> dict[str, object]:
    """List Stripe subscriptions.

    Args:
        settings: Loaded settings.
        limit: Max records.
        customer: Optional customer ID filter.
        status: Optional status filter (active, canceled, etc.).
        starting_after: Cursor for pagination.

    Returns:
        List payload.

    Raises:
        ToolsetError: If API request fails.
    """

    client = StripeClient(settings=settings)
    return await client.list_subscriptions(
        limit=limit, customer=customer, status=status, starting_after=starting_after
    )


async def run_get_subscription(settings: AITSettings, subscription_id: str) -> dict[str, object]:
    """Get a Stripe subscription by ID.

    Args:
        settings: Loaded settings.
        subscription_id: Stripe subscription identifier.

    Returns:
        Subscription payload.

    Raises:
        ToolsetError: If API request fails.
    """

    client = StripeClient(settings=settings)
    return await client.get_subscription(subscription_id)
