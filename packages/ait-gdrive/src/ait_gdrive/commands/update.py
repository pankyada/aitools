"""Drive update command handlers."""

from __future__ import annotations

from pathlib import Path

from ait_core.config.settings import AITSettings

from ait_gdrive.client import DriveClient
from ait_gdrive.scopes import SCOPES_FULL


async def run_update(
    settings: AITSettings,
    file_id_or_path: str,
    local_file: Path | None,
    rename: str | None,
) -> dict[str, object]:
    """Update Drive file content and/or name.

    Args:
        settings: Loaded settings.
        file_id_or_path: Target file path/ID.
        local_file: Optional replacement file path.
        rename: Optional new name.

    Returns:
        Update payload.

    Raises:
        ToolsetError: If API fails.
    """

    client = DriveClient(settings=settings, scopes=SCOPES_FULL)
    file_id = (
        await client.resolve_path(file_id_or_path)
        if "/" in file_id_or_path or file_id_or_path == "root"
        else file_id_or_path
    )
    return await client.update_file(file_id=file_id, local_path=local_file, rename=rename)
