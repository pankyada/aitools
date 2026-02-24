"""Store memory command handler."""

from __future__ import annotations

from ait_core.config.settings import AITSettings

from ait_memory.db import MemoryDB
from ait_memory.embeddings import EmbeddingProvider
from ait_memory.entities import extract_entities, extract_relationships


async def run_store(
    settings: AITSettings,
    text: str,
    source: str,
    source_ref: str | None,
    importance: float,
    extract: bool,
    embed: bool,
) -> dict[str, object]:
    """Store a memory record and optional derived data.

    Args:
        settings: Loaded settings.
        text: Memory text.
        source: Source label.
        source_ref: Optional source reference.
        importance: Initial importance score.
        extract: Whether to run entity extraction.
        embed: Whether to generate embeddings.

    Returns:
        Store result payload.

    Raises:
        ToolsetError: If database operations fail.
    """

    db = MemoryDB(settings)
    db.init_db()

    entities = extract_entities(text) if extract else []
    relationships = extract_relationships(text, entities) if extract else []

    vector = None
    if embed:
        provider = EmbeddingProvider(settings)
        vector = await provider.embed(text)

    return db.store_memory(
        content=text,
        source=source,
        source_ref=source_ref,
        importance=importance,
        embedding=vector,
        entities=entities,
        relationships=relationships,
    )
