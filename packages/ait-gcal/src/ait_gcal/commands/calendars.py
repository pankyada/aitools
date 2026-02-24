"""Calendar list command handlers."""

from __future__ import annotations

from ait_core.config.settings import AITSettings

from ait_gcal.client import GCalClient
from ait_gcal.scopes import SCOPES_READ


async def run_list_calendars(settings: AITSettings, max_results: int) -> dict[str, object]:
    """List calendars available to the user.

    Args:
        settings: Loaded settings.
        max_results: Maximum returned calendars.

    Returns:
        Calendar list payload.

    Raises:
        ToolsetError: If API call fails.
    """

    client = GCalClient(settings=settings, scopes=SCOPES_READ)
    return await client.list_calendars(max_results=max_results)
