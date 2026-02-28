"""Stripe invoices command handlers."""

from __future__ import annotations

from ait_core.config.settings import AITSettings

from ait_stripe.client import StripeClient


async def run_list_invoices(
    settings: AITSettings,
    limit: int = 20,
    customer: str | None = None,
    starting_after: str | None = None,
) -> dict[str, object]:
    """List Stripe invoices.

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
    return await client.list_invoices(
        limit=limit, customer=customer, starting_after=starting_after
    )


async def run_get_invoice(settings: AITSettings, invoice_id: str) -> dict[str, object]:
    """Get a Stripe invoice by ID.

    Args:
        settings: Loaded settings.
        invoice_id: Stripe invoice identifier.

    Returns:
        Invoice payload.

    Raises:
        ToolsetError: If API request fails.
    """

    client = StripeClient(settings=settings)
    return await client.get_invoice(invoice_id)
