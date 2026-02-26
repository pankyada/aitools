"""Image generation command handler."""

from __future__ import annotations

from pathlib import Path

from ait_core.config.settings import AITSettings

from ait_xai.client import XAIClient
from ait_xai.models import ImageRequest


async def run_image(
    settings: AITSettings,
    prompt: str,
    output: Path | None,
    size: str | None,
    model: str | None,
    num: int,
) -> dict[str, object]:
    """Generate images and optionally save one to disk.

    Args:
        settings: Loaded settings.
        prompt: Prompt text.
        output: Optional output path.
        size: Requested image size.
        model: Optional model override.
        num: Number of images.

    Returns:
        Payload with generated image metadata.

    Raises:
        ToolsetError: If API call fails.
    """

    client = XAIClient(settings=settings)
    request = ImageRequest(model=model or settings.xai.image_model, prompt=prompt, size=size, n=num)
    result = await client.generate_image(request)

    saved_path: str | None = None
    if output and result.images:
        await client.save_image_payload(result.images[0], output)
        saved_path = str(output)

    payload = result.model_dump(exclude_none=True)
    payload["saved_path"] = saved_path
    return payload
