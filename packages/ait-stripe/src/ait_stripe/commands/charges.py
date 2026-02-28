"""Stripe charges command handlers."""

from __future__ import annotations

from ait_core.config.settings import AITSettings

from ait_stripe.client import StripeClient


async def run_list_charges(
    settings: AITSettings,
    limit: int = 20,
    customer: str | None = None,
    starting_after: str | None = None,
) -> dict[str, object]:
    """List Stripe charges.

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
    return await client.list_charges(limit=limit, customer=customer, starting_after=starting_after)


async def run_get_charge(settings: AITSettings, charge_id: str) -> dict[str, object]:
    """Get a Stripe charge by ID.

    Args:
        settings: Loaded settings.
        charge_id: Stripe charge identifier.

    Returns:
        Charge payload.

    Raises:
        ToolsetError: If API request fails.
    """

    client = StripeClient(settings=settings)
    return await client.get_charge(charge_id)
