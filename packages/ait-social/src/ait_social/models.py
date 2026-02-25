"""Pydantic models for social platform operations."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

SocialPlatform = Literal["instagram", "facebook", "twitter", "linkedin", "tiktok"]


class SocialPostRequest(BaseModel):
    """Unified social post creation request."""

    platform: SocialPlatform
    text: str | None = None
    title: str | None = None
    media_url: str | None = None
    link_url: str | None = None
    account_id: str | None = None
    visibility: str | None = None
    extra: dict[str, Any] = Field(default_factory=dict)


class SocialPostResult(BaseModel):
    """Unified social post response."""

    platform: SocialPlatform
    id: str | None = None
    status: str | None = None
    url: str | None = None
    raw: dict[str, Any] = Field(default_factory=dict)


class SocialProfileResult(BaseModel):
    """Unified social profile response."""

    platform: SocialPlatform
    account_id: str | None = None
    display_name: str | None = None
    username: str | None = None
    followers: int | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
