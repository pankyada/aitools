"""Pydantic models for xAI command inputs and outputs."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """Single chat message payload."""

    role: str
    content: str


class ChatRequest(BaseModel):
    """Request payload for chat completions."""

    model: str
    messages: list[ChatMessage]
    temperature: float = 0.7
    max_tokens: int | None = None
    stream: bool = False
    response_format: dict[str, str] | None = None


class ChatResult(BaseModel):
    """Normalized chat output payload."""

    model: str
    content: str
    finish_reason: str | None = None


class ImageRequest(BaseModel):
    """Request payload for image generation."""

    model: str
    prompt: str
    size: str = "1024x1024"
    n: int = Field(default=1, ge=1, le=10)


class ImageResult(BaseModel):
    """Normalized image generation result."""

    created: int | None = None
    images: list[str]


class VideoRequest(BaseModel):
    """Request payload for video generation."""

    model: str
    prompt: str
    duration: int | None = None


class VideoResult(BaseModel):
    """Normalized video generation result."""

    id: str | None = None
    status: str | None = None
    output_url: str | None = None
