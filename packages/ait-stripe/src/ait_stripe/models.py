"""Pydantic models for ait-stripe."""

from __future__ import annotations

from pydantic import BaseModel


class StripeListParams(BaseModel):
    """Common parameters for Stripe list endpoints."""

    limit: int = 20
    customer: str | None = None
    status: str | None = None
    starting_after: str | None = None
