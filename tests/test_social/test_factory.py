"""Tests for social provider factory."""

from __future__ import annotations

import pytest
from ait_social.provider_factory import create_provider
from ait_social.providers.facebook import FacebookProvider
from ait_social.providers.instagram import InstagramProvider
from ait_social.providers.linkedin import LinkedInProvider
from ait_social.providers.tiktok import TikTokProvider
from ait_social.providers.twitter import TwitterProvider


def test_factory_returns_expected_provider_types() -> None:
    """Factory should map each platform to the correct provider class."""

    assert isinstance(create_provider("instagram", "tok"), InstagramProvider)
    assert isinstance(create_provider("facebook", "tok"), FacebookProvider)
    assert isinstance(create_provider("twitter", "tok"), TwitterProvider)
    assert isinstance(create_provider("linkedin", "tok"), LinkedInProvider)
    assert isinstance(create_provider("tiktok", "tok"), TikTokProvider)


def test_factory_rejects_unknown_platform() -> None:
    """Unknown platforms should raise value errors."""

    with pytest.raises(ValueError):
        create_provider("unknown", "tok")  # type: ignore[arg-type]
