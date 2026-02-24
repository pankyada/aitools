"""Event command handlers."""

from __future__ import annotations

from ait_core.config.settings import AITSettings

from ait_gcal.client import GCalClient
from ait_gcal.scopes import SCOPES_EVENTS, SCOPES_READ


async def run_list_events(
    settings: AITSettings,
    calendar_id: str,
    max_results: int,
    time_min: str | None,
    time_max: str | None,
    query: str | None,
) -> dict[str, object]:
    """List calendar events.

    Args:
        settings: Loaded settings.
        calendar_id: Calendar id.
        max_results: Maximum events.
        time_min: Optional lower bound.
        time_max: Optional upper bound.
        query: Optional search term.

    Returns:
        Event list payload.

    Raises:
        ToolsetError: If API call fails.
    """

    client = GCalClient(settings=settings, scopes=SCOPES_READ)
    normalized_min = GCalClient.normalize_rfc3339(time_min) if time_min else None
    normalized_max = GCalClient.normalize_rfc3339(time_max) if time_max else None
    return await client.list_events(
        calendar_id=calendar_id,
        max_results=max_results,
        time_min=normalized_min,
        time_max=normalized_max,
        query=query,
    )


async def run_get_event(
    settings: AITSettings, calendar_id: str, event_id: str
) -> dict[str, object]:
    """Get an event by id.

    Args:
        settings: Loaded settings.
        calendar_id: Calendar id.
        event_id: Event id.

    Returns:
        Event payload.

    Raises:
        ToolsetError: If API call fails.
    """

    client = GCalClient(settings=settings, scopes=SCOPES_READ)
    return await client.get_event(calendar_id=calendar_id, event_id=event_id)


async def run_create_event(
    settings: AITSettings,
    calendar_id: str,
    summary: str,
    start: str,
    end: str,
    description: str | None,
    location: str | None,
    timezone: str | None,
) -> dict[str, object]:
    """Create event in calendar.

    Args:
        settings: Loaded settings.
        calendar_id: Calendar id.
        summary: Event title.
        start: Start datetime.
        end: End datetime.
        description: Optional description.
        location: Optional location.
        timezone: Optional timezone.

    Returns:
        Created event payload.

    Raises:
        ToolsetError: If API call fails.
    """

    client = GCalClient(settings=settings, scopes=SCOPES_EVENTS)
    normalized_start = GCalClient.normalize_rfc3339(start)
    normalized_end = GCalClient.normalize_rfc3339(end)
    return await client.create_event(
        calendar_id=calendar_id,
        summary=summary,
        start=normalized_start,
        end=normalized_end,
        description=description,
        location=location,
        timezone=timezone,
    )


async def run_delete_event(
    settings: AITSettings, calendar_id: str, event_id: str
) -> dict[str, object]:
    """Delete event from calendar.

    Args:
        settings: Loaded settings.
        calendar_id: Calendar id.
        event_id: Event id.

    Returns:
        Delete payload.

    Raises:
        ToolsetError: If API call fails.
    """

    client = GCalClient(settings=settings, scopes=SCOPES_EVENTS)
    return await client.delete_event(calendar_id=calendar_id, event_id=event_id)
