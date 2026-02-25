"""Shared command handlers for social CLI."""

from __future__ import annotations

from typing import Any

from ait_core.auth.api_key_store import APIKeyStore
from ait_core.config.settings import AITSettings
from ait_core.errors import ErrorCode, ExitCode, ToolsetError

from ait_social.models import SocialPlatform, SocialPostRequest
from ait_social.provider_factory import create_provider

SOCIAL_PLATFORMS: tuple[SocialPlatform, ...] = (
    "instagram",
    "facebook",
    "twitter",
    "linkedin",
    "tiktok",
)


def service_name_for_platform(platform: SocialPlatform) -> str:
    """Map platform key to API key storage key.

    Args:
        platform: Social platform enum value.

    Returns:
        Service key name used by APIKeyStore.

    Raises:
        None.
    """

    return f"social_{platform}"


def get_platform_token(
    settings: AITSettings,
    platform: SocialPlatform,
    key_store: APIKeyStore | None = None,
) -> str:
    """Resolve API token from settings or encrypted store.

    Args:
        settings: Loaded settings.
        platform: Target platform.
        key_store: Optional key-store instance.

    Returns:
        Access token string.

    Raises:
        ToolsetError: If token is missing.
    """

    _ = settings
    store = key_store or APIKeyStore()
    token = store.get_key(service_name_for_platform(platform))
    if not token:
        raise ToolsetError(
            code=ErrorCode.AUTH_ERROR,
            message=(
                f"No token configured for {platform}. "
                f"Use `ait-social auth set-token --platform {platform}`."
            ),
            exit_code=ExitCode.AUTH_ERROR,
        )
    return token


async def run_create_post(
    settings: AITSettings,
    platform: SocialPlatform,
    text: str | None,
    title: str | None,
    media_url: str | None,
    link_url: str | None,
    account_id: str | None,
    visibility: str | None,
    extra: dict[str, Any] | None,
) -> dict[str, object]:
    """Create social media post.

    Args:
        settings: Loaded settings.
        platform: Target platform.
        text: Post text.
        title: Optional title.
        media_url: Optional media URL.
        link_url: Optional link URL.
        account_id: Optional account identifier.
        visibility: Optional visibility level.
        extra: Optional provider-specific extras.

    Returns:
        Post result payload.

    Raises:
        ToolsetError: If auth/provider call fails.
    """

    token = get_platform_token(settings=settings, platform=platform)
    provider = create_provider(platform=platform, access_token=token)
    request = SocialPostRequest(
        platform=platform,
        text=text,
        title=title,
        media_url=media_url,
        link_url=link_url,
        account_id=account_id,
        visibility=visibility,
        extra=extra or {},
    )
    result = await provider.create_post(request)
    return result.model_dump(exclude_none=True)


async def run_get_profile(
    settings: AITSettings,
    platform: SocialPlatform,
    account_id: str | None,
) -> dict[str, object]:
    """Get profile metadata from provider.

    Args:
        settings: Loaded settings.
        platform: Target platform.
        account_id: Optional account identifier.

    Returns:
        Profile payload.

    Raises:
        ToolsetError: If auth/provider call fails.
    """

    token = get_platform_token(settings=settings, platform=platform)
    provider = create_provider(platform=platform, access_token=token)
    result = await provider.get_profile(account_id=account_id)
    return result.model_dump(exclude_none=True)
