"""Stripe balance command handler."""

from __future__ import annotations

from ait_core.config.settings import AITSettings

from ait_stripe.client import StripeClient


async def run_balance(settings: AITSettings) -> dict[str, object]:
    """Retrieve Stripe account balance.

    Args:
        settings: Loaded settings.

    Returns:
        Balance payload.

    Raises:
        ToolsetError: If API request fails.
    """

    client = StripeClient(settings=settings)
    return await client.get_balance()
