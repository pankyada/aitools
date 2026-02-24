"""Google Drive data models."""

from __future__ import annotations

from pydantic import BaseModel


class DriveFile(BaseModel):
    """Normalized Drive file model."""

    id: str
    name: str
    mime_type: str
    size: int | None = None
    modified_time: str | None = None
    created_time: str | None = None
    parents: list[str] = []
    owners: list[str] = []
    web_view_link: str | None = None
