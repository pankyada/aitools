"""Drive search command handler."""

from __future__ import annotations

from ait_core.config.settings import AITSettings

from ait_gdrive.client import DriveClient
from ait_gdrive.scopes import SCOPES_READ


async def run_search(settings: AITSettings, query: str, max_results: int) -> dict[str, object]:
    """Search Drive files.

    Args:
        settings: Loaded settings.
        query: Drive query syntax.
        max_results: Maximum results.

    Returns:
        Search payload.

    Raises:
        ToolsetError: If API fails.
    """

    client = DriveClient(settings=settings, scopes=SCOPES_READ)
    return await client.search(query=query, max_results=max_results)
