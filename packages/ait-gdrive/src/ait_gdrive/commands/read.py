"""Drive read/download command handler."""

from __future__ import annotations

from pathlib import Path

from ait_core.config.settings import AITSettings

from ait_gdrive.client import DriveClient
from ait_gdrive.scopes import SCOPES_READ


async def run_read(
    settings: AITSettings, file_id_or_path: str, save_to: Path | None
) -> dict[str, object]:
    """Download a Drive file.

    Args:
        settings: Loaded settings.
        file_id_or_path: Drive ID or path.
        save_to: Optional destination path.

    Returns:
        Download payload.

    Raises:
        ToolsetError: If API fails.
    """

    client = DriveClient(settings=settings, scopes=SCOPES_READ)
    file_id = (
        await client.resolve_path(file_id_or_path)
        if "/" in file_id_or_path or file_id_or_path == "root"
        else file_id_or_path
    )
    return await client.download_file(file_id=file_id, destination=save_to)
