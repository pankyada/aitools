"""Drive analysis command handlers."""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from ait_core.config.settings import AITSettings

from ait_gdrive.client import DriveClient
from ait_gdrive.scopes import SCOPES_READ


async def _all_files(settings: AITSettings) -> list[dict[str, object]]:
    """Fetch a broad file sample for analysis.

    Args:
        settings: Loaded settings.

    Returns:
        List of file payloads.

    Raises:
        ToolsetError: If API fails.
    """

    client = DriveClient(settings=settings, scopes=SCOPES_READ)
    payload = await client.list_files(max_results=500)
    return [item for item in payload.get("files", []) if isinstance(item, dict)]


def _as_int(value: object) -> int:
    """Convert loosely-typed value to integer.

    Args:
        value: Candidate value.

    Returns:
        Parsed integer or zero.

    Raises:
        None.
    """

    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0


async def run_storage(settings: AITSettings) -> dict[str, object]:
    """Compute aggregate storage metrics.

    Args:
        settings: Loaded settings.

    Returns:
        Storage summary.

    Raises:
        ToolsetError: If API fails.
    """

    files = await _all_files(settings)
    total_size = sum(_as_int(item.get("size")) for item in files)
    return {"file_count": len(files), "total_size_bytes": total_size}


async def run_duplicates(settings: AITSettings, folder: str | None) -> dict[str, object]:
    """Find duplicate file names.

    Args:
        settings: Loaded settings.
        folder: Optional folder filter (currently advisory only).

    Returns:
        Duplicate groups.

    Raises:
        ToolsetError: If API fails.
    """

    _ = folder
    files = await _all_files(settings)
    names = Counter(str(item.get("name", "")) for item in files)
    dupes = [name for name, count in names.items() if name and count > 1]
    groups = {name: [item for item in files if item.get("name") == name] for name in dupes}
    return {"duplicate_groups": groups, "group_count": len(groups)}


async def run_shared(settings: AITSettings, who: bool) -> dict[str, object]:
    """Analyze shared ownership distribution.

    Args:
        settings: Loaded settings.
        who: Include owner breakdown.

    Returns:
        Shared-file summary.

    Raises:
        ToolsetError: If API fails.
    """

    files = await _all_files(settings)
    owner_counts: Counter[str] = Counter()
    for item in files:
        owners = item.get("owners")
        if isinstance(owners, Iterable) and not isinstance(owners, (str, bytes)):
            for owner in owners:
                owner_counts[str(owner)] += 1

    payload: dict[str, object] = {"unique_owners": len(owner_counts)}
    if who:
        payload["owners"] = owner_counts.most_common(20)
    return payload


async def run_large(settings: AITSettings, top: int, min_size_bytes: int) -> dict[str, object]:
    """Find largest files above threshold.

    Args:
        settings: Loaded settings.
        top: Max number of rows.
        min_size_bytes: Threshold.

    Returns:
        Large-file payload.

    Raises:
        ToolsetError: If API fails.
    """

    files = await _all_files(settings)
    filtered = [item for item in files if _as_int(item.get("size")) >= min_size_bytes]
    filtered.sort(key=lambda item: _as_int(item.get("size")), reverse=True)
    return {"files": filtered[:top], "count": len(filtered)}
