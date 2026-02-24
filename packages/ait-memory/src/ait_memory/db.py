"""SQLite schema and data access for memory tool."""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import ulid
from ait_core.config.settings import AITSettings
from ait_core.errors import ErrorCode, ExitCode, ToolsetError

from ait_memory.entities import ExtractedEntity, ExtractedRelationship
from ait_memory.importance import compute_importance


class MemoryDB:
    """SQLite-backed memory data store.

    Args:
        settings: Loaded settings.

    Returns:
        None.

    Raises:
        OSError: If database directory creation fails.
    """

    def __init__(self, settings: AITSettings) -> None:
        self.settings = settings
        self.db_path = Path(settings.memory.db_path).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def connect(self) -> sqlite3.Connection:
        """Open SQLite connection.

        Args:
            None.

        Returns:
            SQLite connection.

        Raises:
            sqlite3.Error: On connection errors.
        """

        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self) -> None:
        """Create required schema and indexes.

        Args:
            None.

        Returns:
            None.

        Raises:
            sqlite3.Error: On schema errors.
        """

        with self.connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS memories (
                    id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    source TEXT,
                    source_ref TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    importance REAL DEFAULT 0.5,
                    access_count INTEGER DEFAULT 0,
                    last_accessed TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    canonical_name TEXT NOT NULL UNIQUE,
                    entity_type TEXT NOT NULL,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    total_mentions INTEGER DEFAULT 1,
                    recent_mentions INTEGER DEFAULT 0,
                    importance REAL DEFAULT 0.5,
                    metadata TEXT
                );

                CREATE TABLE IF NOT EXISTS relationships (
                    id TEXT PRIMARY KEY,
                    entity_a_id TEXT REFERENCES entities(id),
                    entity_b_id TEXT REFERENCES entities(id),
                    relation_type TEXT NOT NULL,
                    first_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    frequency INTEGER DEFAULT 1,
                    recent_frequency INTEGER DEFAULT 0,
                    importance REAL DEFAULT 0.5,
                    context TEXT,
                    UNIQUE(entity_a_id, entity_b_id, relation_type)
                );

                CREATE TABLE IF NOT EXISTS memory_entities (
                    memory_id TEXT REFERENCES memories(id) ON DELETE CASCADE,
                    entity_id TEXT REFERENCES entities(id) ON DELETE CASCADE,
                    PRIMARY KEY (memory_id, entity_id)
                );

                CREATE TABLE IF NOT EXISTS memory_embeddings (
                    id TEXT PRIMARY KEY,
                    embedding_json TEXT NOT NULL
                );

                CREATE INDEX IF NOT EXISTS idx_memories_created_at ON memories(created_at);
                CREATE INDEX IF NOT EXISTS idx_memories_source ON memories(source);
                CREATE INDEX IF NOT EXISTS idx_memories_importance ON memories(importance);
                CREATE INDEX IF NOT EXISTS idx_entities_canonical ON entities(canonical_name);
                """
            )

    def store_memory(
        self,
        content: str,
        source: str,
        source_ref: str | None,
        importance: float,
        embedding: list[float] | None,
        entities: list[ExtractedEntity],
        relationships: list[ExtractedRelationship],
    ) -> dict[str, Any]:
        """Store memory and update entity graph.

        Args:
            content: Memory text.
            source: Source label.
            source_ref: Optional source reference.
            importance: Initial importance.
            embedding: Optional embedding vector.
            entities: Extracted entities.
            relationships: Extracted relationships.

        Returns:
            Stored memory payload.

        Raises:
            sqlite3.Error: On persistence errors.
        """

        memory_id = str(ulid.new())
        now = datetime.now(tz=UTC).isoformat()

        with self.connect() as conn:
            conn.execute(
                """
                INSERT INTO memories (id, content, source, source_ref, created_at, updated_at, importance)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (memory_id, content, source, source_ref, now, now, importance),
            )

            if embedding is not None:
                conn.execute(
                    "INSERT INTO memory_embeddings (id, embedding_json) VALUES (?, ?)",
                    (memory_id, json.dumps(embedding)),
                )

            entity_id_by_canonical: dict[str, str] = {}
            for entity in entities:
                existing = conn.execute(
                    "SELECT id, total_mentions, access_count, julianday('now') - julianday(last_seen) AS recency_days FROM entities WHERE canonical_name = ?",
                    (entity.canonical_name,),
                ).fetchone()

                if existing:
                    entity_id = str(existing["id"])
                    total_mentions = int(existing["total_mentions"]) + 1
                    recency_days = float(existing["recency_days"] or 0.0)
                    score = compute_importance(
                        total_mentions=total_mentions,
                        recent_mentions=1,
                        recency_days=recency_days,
                        access_count=int(existing["access_count"] or 0),
                    )
                    conn.execute(
                        """
                        UPDATE entities
                        SET name = ?, last_seen = ?, total_mentions = ?, recent_mentions = recent_mentions + 1, importance = ?
                        WHERE id = ?
                        """,
                        (entity.name, now, total_mentions, score, entity_id),
                    )
                else:
                    entity_id = str(ulid.new())
                    conn.execute(
                        """
                        INSERT INTO entities (
                            id, name, canonical_name, entity_type, first_seen, last_seen,
                            total_mentions, recent_mentions, importance, metadata
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            entity_id,
                            entity.name,
                            entity.canonical_name,
                            entity.entity_type,
                            now,
                            now,
                            1,
                            1,
                            0.5,
                            None,
                        ),
                    )

                entity_id_by_canonical[entity.canonical_name] = entity_id
                conn.execute(
                    "INSERT OR IGNORE INTO memory_entities (memory_id, entity_id) VALUES (?, ?)",
                    (memory_id, entity_id),
                )

            for rel in relationships:
                entity_a_id = entity_id_by_canonical.get(rel.entity_a)
                entity_b_id = entity_id_by_canonical.get(rel.entity_b)
                if entity_a_id is None or entity_b_id is None:
                    continue

                existing_rel = conn.execute(
                    """
                    SELECT id, frequency, julianday('now') - julianday(last_seen) AS recency_days
                    FROM relationships
                    WHERE entity_a_id = ? AND entity_b_id = ? AND relation_type = ?
                    """,
                    (entity_a_id, entity_b_id, rel.relation_type),
                ).fetchone()

                if existing_rel:
                    rel_id = str(existing_rel["id"])
                    frequency = int(existing_rel["frequency"]) + 1
                    score = compute_importance(
                        total_mentions=frequency,
                        recent_mentions=1,
                        recency_days=float(existing_rel["recency_days"] or 0.0),
                    )
                    conn.execute(
                        """
                        UPDATE relationships
                        SET last_seen = ?, frequency = ?, recent_frequency = recent_frequency + 1,
                            importance = ?, context = ?
                        WHERE id = ?
                        """,
                        (now, frequency, score, rel.context, rel_id),
                    )
                else:
                    conn.execute(
                        """
                        INSERT INTO relationships (
                            id, entity_a_id, entity_b_id, relation_type, first_seen,
                            last_seen, frequency, recent_frequency, importance, context
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        """,
                        (
                            str(ulid.new()),
                            entity_a_id,
                            entity_b_id,
                            rel.relation_type,
                            now,
                            now,
                            1,
                            1,
                            0.5,
                            rel.context,
                        ),
                    )

        return {
            "id": memory_id,
            "source": source,
            "source_ref": source_ref,
            "importance": importance,
            "entities": [entity.canonical_name for entity in entities],
        }

    def get_memory(self, memory_id: str) -> dict[str, Any]:
        """Fetch memory by ID.

        Args:
            memory_id: Memory ID.

        Returns:
            Memory payload.

        Raises:
            ToolsetError: If memory not found.
        """

        with self.connect() as conn:
            row = conn.execute("SELECT * FROM memories WHERE id = ?", (memory_id,)).fetchone()
            if row is None:
                raise ToolsetError(
                    code=ErrorCode.NOT_FOUND,
                    message=f"Memory not found: {memory_id}",
                    exit_code=ExitCode.NOT_FOUND,
                )

            conn.execute(
                """
                UPDATE memories
                SET access_count = access_count + 1,
                    last_accessed = ?
                WHERE id = ?
                """,
                (datetime.now(tz=UTC).isoformat(), memory_id),
            )
            return dict(row)

    def get_recent(self, limit: int) -> list[dict[str, Any]]:
        """Fetch recent memories.

        Args:
            limit: Result limit.

        Returns:
            Memory rows.

        Raises:
            None.
        """

        with self.connect() as conn:
            rows = conn.execute(
                "SELECT * FROM memories ORDER BY created_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
            return [dict(row) for row in rows]

    def get_by_entity(self, entity_name: str) -> list[dict[str, Any]]:
        """Fetch memories linked to an entity.

        Args:
            entity_name: Entity canonical or display name.

        Returns:
            Matching memory rows.

        Raises:
            None.
        """

        canonical = entity_name.lower()
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT m.*
                FROM memories m
                JOIN memory_entities me ON m.id = me.memory_id
                JOIN entities e ON e.id = me.entity_id
                WHERE e.canonical_name = ? OR e.name = ?
                ORDER BY m.created_at DESC
                """,
                (canonical, entity_name),
            ).fetchall()
            return [dict(row) for row in rows]

    def keyword_search(self, query: str, limit: int) -> list[dict[str, Any]]:
        """Run keyword-like search using SQL LIKE.

        Args:
            query: Search term.
            limit: Result limit.

        Returns:
            Matching memories with keyword scores.

        Raises:
            None.
        """

        pattern = f"%{query}%"
        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT *,
                    CASE WHEN content LIKE ? THEN 1.0 ELSE 0.0 END AS keyword_score
                FROM memories
                WHERE content LIKE ?
                ORDER BY importance DESC, created_at DESC
                LIMIT ?
                """,
                (pattern, pattern, limit),
            ).fetchall()
            return [dict(row) for row in rows]

    def semantic_search(self, query_embedding: list[float], limit: int) -> list[dict[str, Any]]:
        """Run semantic search using cosine similarity in Python.

        Args:
            query_embedding: Query embedding vector.
            limit: Result limit.

        Returns:
            Ranked memory rows with semantic scores.

        Raises:
            None.
        """

        with self.connect() as conn:
            rows = conn.execute(
                """
                SELECT m.*, me.embedding_json
                FROM memories m
                JOIN memory_embeddings me ON me.id = m.id
                """
            ).fetchall()

        scored: list[dict[str, Any]] = []
        for row in rows:
            item = dict(row)
            embedding_raw = item.pop("embedding_json", None)
            if not isinstance(embedding_raw, str):
                continue
            candidate = json.loads(embedding_raw)
            if not isinstance(candidate, list):
                continue
            vector = [float(v) for v in candidate]
            score = _cosine_similarity(query_embedding, vector)
            item["semantic_score"] = score
            scored.append(item)

        scored.sort(key=lambda value: float(value.get("semantic_score") or 0.0), reverse=True)
        return scored[:limit]

    def list_entities(self, sort: str) -> list[dict[str, Any]]:
        """List entities with optional sorting.

        Args:
            sort: Sort key.

        Returns:
            Entity rows.

        Raises:
            None.
        """

        order = "importance DESC" if sort == "importance" else "last_seen DESC"
        with self.connect() as conn:
            rows = conn.execute(f"SELECT * FROM entities ORDER BY {order}").fetchall()
            return [dict(row) for row in rows]

    def get_entity(self, name: str) -> dict[str, Any]:
        """Get single entity.

        Args:
            name: Name or canonical name.

        Returns:
            Entity payload.

        Raises:
            ToolsetError: If entity missing.
        """

        with self.connect() as conn:
            row = conn.execute(
                "SELECT * FROM entities WHERE canonical_name = ? OR name = ?",
                (name.lower(), name),
            ).fetchone()
            if row is None:
                raise ToolsetError(
                    code=ErrorCode.NOT_FOUND,
                    message=f"Entity not found: {name}",
                    exit_code=ExitCode.NOT_FOUND,
                )
            return dict(row)

    def get_relationships(self, name: str) -> list[dict[str, Any]]:
        """List relationships for an entity.

        Args:
            name: Entity name/canonical name.

        Returns:
            Relationship rows.

        Raises:
            ToolsetError: If entity missing.
        """

        with self.connect() as conn:
            entity = conn.execute(
                "SELECT id FROM entities WHERE canonical_name = ? OR name = ?",
                (name.lower(), name),
            ).fetchone()
            if entity is None:
                raise ToolsetError(
                    code=ErrorCode.NOT_FOUND,
                    message=f"Entity not found: {name}",
                    exit_code=ExitCode.NOT_FOUND,
                )

            rows = conn.execute(
                """
                SELECT r.*, ea.name AS entity_a_name, eb.name AS entity_b_name
                FROM relationships r
                JOIN entities ea ON ea.id = r.entity_a_id
                JOIN entities eb ON eb.id = r.entity_b_id
                WHERE r.entity_a_id = ? OR r.entity_b_id = ?
                ORDER BY r.importance DESC, r.frequency DESC
                """,
                (entity["id"], entity["id"]),
            ).fetchall()
            return [dict(row) for row in rows]

    def stats(self) -> dict[str, Any]:
        """Return high-level DB metrics.

        Args:
            None.

        Returns:
            Stats payload.

        Raises:
            None.
        """

        with self.connect() as conn:
            mem_count = conn.execute("SELECT COUNT(*) AS c FROM memories").fetchone()["c"]
            entity_count = conn.execute("SELECT COUNT(*) AS c FROM entities").fetchone()["c"]
            rel_count = conn.execute("SELECT COUNT(*) AS c FROM relationships").fetchone()["c"]
        return {
            "db_path": str(self.db_path),
            "memories": int(mem_count),
            "entities": int(entity_count),
            "relationships": int(rel_count),
        }

    def forget(self, ids: list[str]) -> dict[str, Any]:
        """Delete memories by ID.

        Args:
            ids: Memory IDs.

        Returns:
            Delete summary.

        Raises:
            None.
        """

        with self.connect() as conn:
            for memory_id in ids:
                conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
                conn.execute("DELETE FROM memory_embeddings WHERE id = ?", (memory_id,))
                conn.execute("DELETE FROM memory_entities WHERE memory_id = ?", (memory_id,))
        return {"deleted": len(ids), "memory_ids": ids}

    def compact(self, prune_threshold: float | None = None) -> dict[str, Any]:
        """Recompute importance and optionally prune low-importance memories.

        Args:
            prune_threshold: Optional prune threshold.

        Returns:
            Compaction summary.

        Raises:
            None.
        """

        now = datetime.now(tz=UTC)
        updated_entities = 0
        updated_relationships = 0
        pruned = 0

        with self.connect() as conn:
            entities = conn.execute("SELECT * FROM entities").fetchall()
            for row in entities:
                recency_days = (now - datetime.fromisoformat(str(row["last_seen"]))).days
                score = compute_importance(
                    total_mentions=int(row["total_mentions"]),
                    recent_mentions=int(row["recent_mentions"]),
                    recency_days=float(recency_days),
                    access_count=0,
                )
                conn.execute("UPDATE entities SET importance = ? WHERE id = ?", (score, row["id"]))
                updated_entities += 1

            rels = conn.execute("SELECT * FROM relationships").fetchall()
            for row in rels:
                recency_days = (now - datetime.fromisoformat(str(row["last_seen"]))).days
                score = compute_importance(
                    total_mentions=int(row["frequency"]),
                    recent_mentions=int(row["recent_frequency"]),
                    recency_days=float(recency_days),
                )
                conn.execute(
                    "UPDATE relationships SET importance = ? WHERE id = ?", (score, row["id"])
                )
                updated_relationships += 1

            if prune_threshold is not None:
                rows = conn.execute(
                    "SELECT id FROM memories WHERE importance < ?",
                    (prune_threshold,),
                ).fetchall()
                ids = [str(row["id"]) for row in rows]
                if ids:
                    qmarks = ",".join("?" for _ in ids)
                    conn.execute(f"DELETE FROM memories WHERE id IN ({qmarks})", ids)
                    conn.execute(f"DELETE FROM memory_embeddings WHERE id IN ({qmarks})", ids)
                    conn.execute(f"DELETE FROM memory_entities WHERE memory_id IN ({qmarks})", ids)
                    pruned = len(ids)

        return {
            "updated_entities": updated_entities,
            "updated_relationships": updated_relationships,
            "pruned_memories": pruned,
        }


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Compute cosine similarity between vectors.

    Args:
        a: Vector A.
        b: Vector B.

    Returns:
        Cosine similarity in [-1.0, 1.0].

    Raises:
        None.
    """

    if not a or not b or len(a) != len(b):
        return 0.0

    dot: float = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a: float = sum(x * x for x in a) ** 0.5
    norm_b: float = sum(y * y for y in b) ** 0.5
    if norm_a == 0.0 or norm_b == 0.0:
        return 0.0
    return float(dot / (norm_a * norm_b))
