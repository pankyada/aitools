"""Video generation command handler."""

from __future__ import annotations

from ait_core.config.settings import AITSettings

from ait_xai.client import XAIClient
from ait_xai.models import VideoRequest


async def run_video(
    settings: AITSettings,
    prompt: str,
    duration: int | None,
    model: str | None,
) -> dict[str, object]:
    """Generate a video request from prompt text.

    Args:
        settings: Loaded settings.
        prompt: Prompt text.
        duration: Optional duration in seconds.
        model: Optional model override.

    Returns:
        Video generation payload.

    Raises:
        ToolsetError: If API call fails.
    """

    client = XAIClient(settings=settings)
    request = VideoRequest(
        model=model or settings.xai.default_model, prompt=prompt, duration=duration
    )
    result = await client.generate_video(request)
    return result.model_dump(exclude_none=True)
