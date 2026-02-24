"""Drive list command handler."""

from __future__ import annotations

from ait_core.config.settings import AITSettings

from ait_gdrive.client import DriveClient
from ait_gdrive.scopes import SCOPES_READ


async def run_list(
    settings: AITSettings, path_value: str | None, max_results: int
) -> dict[str, object]:
    """List files under optional path.

    Args:
        settings: Loaded settings.
        path_value: Optional folder path/ID.
        max_results: Maximum results.

    Returns:
        File list payload.

    Raises:
        ToolsetError: If API fails.
    """

    client = DriveClient(settings=settings, scopes=SCOPES_READ)
    parent: str | None = None
    if path_value:
        parent = await client.resolve_path(path_value)
    return await client.list_files(parent_id=parent, max_results=max_results)
