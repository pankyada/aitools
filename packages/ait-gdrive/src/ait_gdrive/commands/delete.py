"""Drive delete command handler."""

from __future__ import annotations

from ait_core.config.settings import AITSettings

from ait_gdrive.client import DriveClient
from ait_gdrive.scopes import SCOPES_FULL


async def run_delete(
    settings: AITSettings,
    targets: list[str],
    permanent: bool,
) -> dict[str, object]:
    """Delete one or more Drive files.

    Args:
        settings: Loaded settings.
        targets: Target IDs/paths.
        permanent: Permanent-delete flag.

    Returns:
        Delete summary payload.

    Raises:
        ToolsetError: If API fails.
    """

    client = DriveClient(settings=settings, scopes=SCOPES_FULL)
    results: list[dict[str, object]] = []
    for target in targets:
        file_id = await client.resolve_path(target) if "/" in target or target == "root" else target
        results.append(await client.delete_file(file_id=file_id, permanent=permanent))
    return {"deleted": len(results), "results": results}
