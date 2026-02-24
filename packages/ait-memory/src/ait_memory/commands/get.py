"""Get memory command handler."""

from __future__ import annotations

from ait_core.config.settings import AITSettings

from ait_memory.db import MemoryDB


async def run_get(
    settings: AITSettings,
    memory_id: str | None,
    entity: str | None,
    recent: bool,
    limit: int,
) -> dict[str, object]:
    """Get memory records by ID, entity, or recency.

    Args:
        settings: Loaded settings.
        memory_id: Optional memory ID.
        entity: Optional entity name.
        recent: Whether to fetch recent entries.
        limit: Max rows for recent mode.

    Returns:
        Retrieval payload.

    Raises:
        ToolsetError: If selected memory/entity is not found.
    """

    db = MemoryDB(settings)
    db.init_db()

    if memory_id:
        return {"memory": db.get_memory(memory_id)}
    if entity:
        return {"memories": db.get_by_entity(entity), "entity": entity}
    if recent:
        return {"memories": db.get_recent(limit), "limit": limit}
    return {"memories": [], "note": "No selector provided"}
