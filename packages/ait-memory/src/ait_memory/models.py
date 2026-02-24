"""Pydantic models for memory objects."""

from __future__ import annotations

from pydantic import BaseModel, Field


class MemoryRecord(BaseModel):
    """Stored memory representation."""

    id: str
    content: str
    source: str | None = None
    source_ref: str | None = None
    created_at: str
    updated_at: str
    importance: float = Field(ge=0.0, le=1.0)
    access_count: int = 0
    last_accessed: str | None = None


class EntityRecord(BaseModel):
    """Stored entity representation."""

    id: str
    name: str
    canonical_name: str
    entity_type: str
    first_seen: str
    last_seen: str
    total_mentions: int
    recent_mentions: int
    importance: float
    metadata: str | None = None


class RelationshipRecord(BaseModel):
    """Stored relationship representation."""

    id: str
    entity_a_id: str
    entity_b_id: str
    relation_type: str
    first_seen: str
    last_seen: str
    frequency: int
    recent_frequency: int
    importance: float
    context: str | None = None
