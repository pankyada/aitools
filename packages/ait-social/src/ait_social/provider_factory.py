"""Factory for social provider instances."""

from __future__ import annotations

import httpx

from ait_social.models import SocialPlatform
from ait_social.providers import (
    FacebookProvider,
    InstagramProvider,
    LinkedInProvider,
    TikTokProvider,
    TwitterProvider,
)
from ait_social.providers.base import SocialProvider


def create_provider(
    platform: SocialPlatform,
    access_token: str,
    http_client: httpx.AsyncClient | None = None,
) -> SocialProvider:
    """Instantiate provider for the requested platform.

    Args:
        platform: Target social platform.
        access_token: Provider OAuth/Bearer token.
        http_client: Optional async HTTP client.

    Returns:
        SocialProvider instance.

    Raises:
        ValueError: If platform value is unsupported.
    """

    if platform == "instagram":
        return InstagramProvider(access_token=access_token, http_client=http_client)
    if platform == "facebook":
        return FacebookProvider(access_token=access_token, http_client=http_client)
    if platform == "twitter":
        return TwitterProvider(access_token=access_token, http_client=http_client)
    if platform == "linkedin":
        return LinkedInProvider(access_token=access_token, http_client=http_client)
    if platform == "tiktok":
        return TikTokProvider(access_token=access_token, http_client=http_client)
    raise ValueError(f"Unsupported social platform: {platform}")
