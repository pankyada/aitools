"""Gmail data models."""

from __future__ import annotations

from pydantic import BaseModel


class EmailAddress(BaseModel):
    """Parsed email address."""

    name: str | None = None
    email: str


class MessageSummary(BaseModel):
    """Summarized Gmail message model."""

    id: str
    thread_id: str
    from_: EmailAddress
    to: list[EmailAddress]
    subject: str | None = None
    snippet: str | None = None
    date: str | None = None
    labels: list[str] = []
    has_attachments: bool = False
    size_bytes: int | None = None


class MessageFull(BaseModel):
    """Detailed Gmail message model."""

    id: str
    thread_id: str
    snippet: str | None = None
    labels: list[str] = []
    internal_date: int | None = None
    payload: dict[str, object] | None = None
    body_text: str | None = None
