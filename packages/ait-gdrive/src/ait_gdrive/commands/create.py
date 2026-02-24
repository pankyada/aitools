"""Drive create/upload command handlers."""

from __future__ import annotations

from pathlib import Path

from ait_core.config.settings import AITSettings

from ait_gdrive.client import DriveClient
from ait_gdrive.scopes import SCOPES_FULL


async def run_create_file(
    settings: AITSettings,
    local_path: Path,
    parent: str | None,
    name: str | None,
) -> dict[str, object]:
    """Upload local file to Drive.

    Args:
        settings: Loaded settings.
        local_path: Source file path.
        parent: Optional parent path/ID.
        name: Optional destination name.

    Returns:
        Upload payload.

    Raises:
        ToolsetError: If API fails.
    """

    client = DriveClient(settings=settings, scopes=SCOPES_FULL)
    parent_id = None
    if parent:
        parent_id = (
            await client.resolve_path(parent) if "/" in parent or parent == "root" else parent
        )
    return await client.upload_file(local_path=local_path, name=name, parent=parent_id)


async def run_create_folder(
    settings: AITSettings, name: str, parent: str | None
) -> dict[str, object]:
    """Create a folder in Drive.

    Args:
        settings: Loaded settings.
        name: Folder name.
        parent: Optional parent path/ID.

    Returns:
        Created folder payload.

    Raises:
        ToolsetError: If API fails.
    """

    client = DriveClient(settings=settings, scopes=SCOPES_FULL)
    parent_id = None
    if parent:
        parent_id = (
            await client.resolve_path(parent) if "/" in parent or parent == "root" else parent
        )
    return await client.create_folder(name=name, parent=parent_id)
