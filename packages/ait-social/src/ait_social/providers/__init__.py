"""Provider registry for social platforms."""

from ait_social.providers.facebook import FacebookProvider
from ait_social.providers.instagram import InstagramProvider
from ait_social.providers.linkedin import LinkedInProvider
from ait_social.providers.tiktok import TikTokProvider
from ait_social.providers.twitter import TwitterProvider

__all__ = [
    "FacebookProvider",
    "InstagramProvider",
    "LinkedInProvider",
    "TikTokProvider",
    "TwitterProvider",
]
