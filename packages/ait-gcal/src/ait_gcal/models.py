"""Google Calendar data models."""

from __future__ import annotations

from pydantic import BaseModel


class CalendarItem(BaseModel):
    """Normalized Google Calendar item."""

    id: str
    summary: str | None = None
    description: str | None = None
    timezone: str | None = None
    primary: bool = False


class EventItem(BaseModel):
    """Normalized Google Calendar event."""

    id: str
    status: str | None = None
    summary: str | None = None
    description: str | None = None
    location: str | None = None
    start: str | None = None
    end: str | None = None
    html_link: str | None = None
    creator_email: str | None = None
