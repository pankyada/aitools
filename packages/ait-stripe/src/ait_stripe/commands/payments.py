"""Stripe payment intents command handlers."""

from __future__ import annotations

from ait_core.config.settings import AITSettings

from ait_stripe.client import StripeClient


async def run_list_payments(
    settings: AITSettings,
    limit: int = 20,
    customer: str | None = None,
    starting_after: str | None = None,
) -> dict[str, object]:
    """List Stripe payment intents.

    Args:
        settings: Loaded settings.
        limit: Max records.
        customer: Optional customer ID filter.
        starting_after: Cursor for pagination.

    Returns:
        List payload.

    Raises:
        ToolsetError: If API request fails.
    """

    client = StripeClient(settings=settings)
    return await client.list_payment_intents(
        limit=limit, customer=customer, starting_after=starting_after
    )


async def run_get_payment(settings: AITSettings, payment_id: str) -> dict[str, object]:
    """Get a Stripe payment intent by ID.

    Args:
        settings: Loaded settings.
        payment_id: Stripe payment intent identifier.

    Returns:
        Payment intent payload.

    Raises:
        ToolsetError: If API request fails.
    """

    client = StripeClient(settings=settings)
    return await client.get_payment_intent(payment_id)
