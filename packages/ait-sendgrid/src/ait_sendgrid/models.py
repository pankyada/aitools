"""Pydantic models for SendGrid payloads."""

from __future__ import annotations

from pydantic import BaseModel, Field


class SendGridEmailRequest(BaseModel):
    """SendGrid send-email request."""

    from_email: str = Field(min_length=1)
    to: list[str] = Field(min_length=1)
    subject: str = Field(min_length=1)
    text: str | None = None
    html: str | None = None
    cc: list[str] = []
    bcc: list[str] = []
    reply_to: str | None = None
