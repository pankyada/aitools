"""Search memory command handler."""

from __future__ import annotations

from datetime import date

from ait_core.config.settings import AITSettings

from ait_memory.db import MemoryDB
from ait_memory.embeddings import EmbeddingProvider


def _as_float(value: object, default: float = 0.0) -> float:
    """Safely coerce scalar object to float.

    Args:
        value: Candidate scalar value.
        default: Fallback value.

    Returns:
        Parsed float or default.

    Raises:
        None.
    """

    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        try:
            return float(value)
        except ValueError:
            return default
    return default


def _rrf_merge(
    semantic: list[dict[str, object]],
    keyword: list[dict[str, object]],
    limit: int,
) -> list[dict[str, object]]:
    """Merge two ranked lists using reciprocal rank fusion.

    Args:
        semantic: Semantic result list.
        keyword: Keyword result list.
        limit: Max results.

    Returns:
        Merged list with `rrf_score` values.

    Raises:
        None.
    """

    k = 60
    score_by_id: dict[str, float] = {}
    item_by_id: dict[str, dict[str, object]] = {}

    for rank, item in enumerate(semantic, start=1):
        item_id = str(item["id"])
        score_by_id[item_id] = score_by_id.get(item_id, 0.0) + 1.0 / (k + rank)
        item_by_id[item_id] = item

    for rank, item in enumerate(keyword, start=1):
        item_id = str(item["id"])
        score_by_id[item_id] = score_by_id.get(item_id, 0.0) + 1.0 / (k + rank)
        item_by_id[item_id] = item

    merged = []
    for item_id, score in score_by_id.items():
        row = dict(item_by_id[item_id])
        row["rrf_score"] = score
        merged.append(row)

    merged.sort(key=lambda row: _as_float(row.get("rrf_score")), reverse=True)
    return merged[:limit]


def _passes_filters(
    item: dict[str, object],
    source: str | None,
    after: date | None,
    before: date | None,
    min_importance: float | None,
) -> bool:
    """Apply scalar/date filters to candidate memory row.

    Args:
        item: Candidate memory row.
        source: Optional source filter.
        after: Optional created-at lower bound.
        before: Optional created-at upper bound.
        min_importance: Optional importance threshold.

    Returns:
        True if item passes all filters.

    Raises:
        ValueError: If created_at parsing fails.
    """

    if source and item.get("source") != source:
        return False
    if min_importance is not None and _as_float(item.get("importance")) < min_importance:
        return False

    created_raw = str(item.get("created_at") or "")
    if created_raw:
        created_dt = date.fromisoformat(created_raw[:10])
        if after and created_dt < after:
            return False
        if before and created_dt > before:
            return False

    return True


async def run_search(
    settings: AITSettings,
    query: str,
    mode: str,
    hybrid: bool,
    entity: str | None,
    source: str | None,
    after: date | None,
    before: date | None,
    min_importance: float | None,
    limit: int,
) -> dict[str, object]:
    """Search memories using keyword, semantic, or hybrid retrieval.

    Args:
        settings: Loaded settings.
        query: Query text.
        mode: Search mode.
        hybrid: Explicit hybrid mode toggle.
        entity: Optional entity filter.
        source: Optional source filter.
        after: Optional lower date bound.
        before: Optional upper date bound.
        min_importance: Optional importance threshold.
        limit: Max returned items.

    Returns:
        Search result payload.

    Raises:
        ToolsetError: If DB or embedding work fails.
    """

    db = MemoryDB(settings)
    db.init_db()

    use_hybrid = hybrid or mode == "hybrid"
    results: list[dict[str, object]] = []

    if use_hybrid:
        provider = EmbeddingProvider(settings)
        query_embedding = await provider.embed(query)
        semantic = db.semantic_search(query_embedding=query_embedding, limit=2 * limit)
        keyword = db.keyword_search(query=query, limit=2 * limit)
        results = _rrf_merge(semantic=semantic, keyword=keyword, limit=2 * limit)
    elif mode == "semantic":
        provider = EmbeddingProvider(settings)
        query_embedding = await provider.embed(query)
        results = db.semantic_search(query_embedding=query_embedding, limit=2 * limit)
    else:
        results = db.keyword_search(query=query, limit=2 * limit)

    if entity:
        allowed = {str(row["id"]) for row in db.get_by_entity(entity)}
        results = [row for row in results if str(row.get("id")) in allowed]

    filtered = [
        row
        for row in results
        if _passes_filters(
            row, source=source, after=after, before=before, min_importance=min_importance
        )
    ]
    final = filtered[:limit]

    for row in final:
        memory_id = str(row["id"])
        db.get_memory(memory_id)

    return {"results": final, "count": len(final), "mode": "hybrid" if use_hybrid else mode}
