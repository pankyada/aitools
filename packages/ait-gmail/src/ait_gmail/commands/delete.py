"""Gmail delete/trash command handlers."""

from __future__ import annotations

from ait_core.config.settings import AITSettings

from ait_gmail.client import GmailClient
from ait_gmail.scopes import SCOPES_MODIFY


async def run_trash(settings: AITSettings, message_ids: list[str]) -> dict[str, object]:
    """Trash messages.

    Args:
        settings: Loaded settings.
        message_ids: Message IDs to trash.

    Returns:
        Action payload.

    Raises:
        ToolsetError: If auth/API fails.
    """

    client = GmailClient(settings=settings, scopes=SCOPES_MODIFY)
    return await client.trash_messages(message_ids)


async def run_permanent(settings: AITSettings, message_ids: list[str]) -> dict[str, object]:
    """Permanently delete messages.

    Args:
        settings: Loaded settings.
        message_ids: Message IDs to delete.

    Returns:
        Action payload.

    Raises:
        ToolsetError: If auth/API fails.
    """

    client = GmailClient(settings=settings, scopes=SCOPES_MODIFY)
    return await client.delete_messages(message_ids)


async def run_bulk(
    settings: AITSettings,
    query: str,
    older_than: int,
    dry_run: bool,
) -> dict[str, object]:
    """Bulk-delete messages matching a query and age filter.

    Args:
        settings: Loaded settings.
        query: Gmail query.
        older_than: Age threshold in days.
        dry_run: When true, only return candidate IDs.

    Returns:
        Action payload.

    Raises:
        ToolsetError: If auth/API fails.
    """

    client = GmailClient(settings=settings, scopes=SCOPES_MODIFY)
    full_query = f"{query} older_than:{older_than}d"
    results = await client.search_messages(query=full_query, max_results=500)
    ids = [str(item["id"]) for item in results.get("messages", []) if isinstance(item, dict)]

    if dry_run:
        return {"dry_run": True, "count": len(ids), "message_ids": ids}

    if not ids:
        return {"deleted": 0, "message_ids": []}
    return await client.delete_messages(ids)
