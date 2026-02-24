"""Read/search Gmail command handlers."""

from __future__ import annotations

from datetime import date

from ait_core.config.settings import AITSettings

from ait_gmail.client import GmailClient
from ait_gmail.scopes import SCOPES_READ


async def run_list(
    settings: AITSettings,
    label: str,
    max_results: int,
    unread: bool,
    after: date | None,
    before: date | None,
    from_filter: str | None,
    has_attachment: bool,
) -> dict[str, object]:
    """List Gmail messages.

    Args:
        settings: Loaded settings.
        label: Label filter.
        max_results: Maximum results.
        unread: Unread-only toggle.
        after: Date lower bound.
        before: Date upper bound.
        from_filter: Sender filter.
        has_attachment: Attachment filter.

    Returns:
        Message listing payload.

    Raises:
        ToolsetError: If auth/API fails.
    """

    client = GmailClient(settings=settings, scopes=SCOPES_READ)
    return await client.list_messages(
        label=label,
        max_results=max_results,
        unread=unread,
        after=after,
        before=before,
        from_filter=from_filter,
        has_attachment=has_attachment,
    )


async def run_get(
    settings: AITSettings,
    message_id: str,
    fmt: str,
    body_only: bool,
) -> dict[str, object]:
    """Get a single Gmail message.

    Args:
        settings: Loaded settings.
        message_id: Message identifier.
        fmt: API fetch format.
        body_only: Return only body text.

    Returns:
        Message payload.

    Raises:
        ToolsetError: If auth/API fails.
    """

    client = GmailClient(settings=settings, scopes=SCOPES_READ)
    message = await client.get_message(message_id=message_id, fmt=fmt)
    if body_only:
        return {"id": message.id, "body": message.body_text or ""}
    return message.model_dump(exclude_none=True)


async def run_search(settings: AITSettings, query: str, max_results: int) -> dict[str, object]:
    """Search Gmail messages.

    Args:
        settings: Loaded settings.
        query: Gmail search query.
        max_results: Maximum results.

    Returns:
        Search payload.

    Raises:
        ToolsetError: If auth/API fails.
    """

    client = GmailClient(settings=settings, scopes=SCOPES_READ)
    return await client.search_messages(query=query, max_results=max_results)


async def run_thread(settings: AITSettings, thread_id: str) -> dict[str, object]:
    """Get a Gmail thread.

    Args:
        settings: Loaded settings.
        thread_id: Thread identifier.

    Returns:
        Thread payload.

    Raises:
        ToolsetError: If auth/API fails.
    """

    client = GmailClient(settings=settings, scopes=SCOPES_READ)
    return await client.get_thread(thread_id)
