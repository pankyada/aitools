"""TikTok API provider."""

from __future__ import annotations

from ait_core.errors import ErrorCode, ExitCode, ToolsetError

from ait_social.models import SocialPostRequest, SocialPostResult, SocialProfileResult
from ait_social.providers.base import SocialProvider


class TikTokProvider(SocialProvider):
    """TikTok provider using Open API publish and user-info endpoints."""

    platform = "tiktok"
    base_url = "https://open.tiktokapis.com/v2"

    def _headers(self) -> dict[str, str]:
        """Build bearer auth headers."""

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def create_post(self, request: SocialPostRequest) -> SocialPostResult:
        """Initialize TikTok video publish from URL."""

        if not request.media_url:
            raise ToolsetError(
                code=ErrorCode.INVALID_INPUT,
                message="TikTok posting requires --media-url (video URL)",
                exit_code=ExitCode.INVALID_INPUT,
            )

        body = {
            "post_info": {
                "title": request.title or request.text or "",
                "privacy_level": request.visibility or "PUBLIC_TO_EVERYONE",
                "disable_comment": False,
                "disable_duet": False,
                "disable_stitch": False,
            },
            "source_info": {
                "source": "PULL_FROM_URL",
                "video_url": request.media_url,
            },
        }

        response = await self._request(
            "POST",
            f"{self.base_url}/post/publish/video/init/",
            headers=self._headers(),
            json=body,
        )
        self.raise_for_status(response, "TikTok")
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else {}
        publish_id = data.get("publish_id") if isinstance(data, dict) else None
        return SocialPostResult(
            platform="tiktok",
            id=str(publish_id) if publish_id else None,
            status="initialized",
            raw=payload if isinstance(payload, dict) else {},
        )

    async def get_profile(self, account_id: str | None = None) -> SocialProfileResult:
        """Get TikTok user information for authenticated user."""

        _ = account_id
        response = await self._request(
            "GET",
            f"{self.base_url}/user/info/",
            headers=self._headers(),
            params={"fields": "open_id,display_name,avatar_url"},
        )
        self.raise_for_status(response, "TikTok")
        payload = response.json()
        data = payload.get("data", {}).get("user") if isinstance(payload, dict) else {}
        if not isinstance(data, dict):
            data = {}
        return SocialProfileResult(
            platform="tiktok",
            account_id=str(data.get("open_id")) if data.get("open_id") else None,
            display_name=data.get("display_name")
            if isinstance(data.get("display_name"), str)
            else None,
            raw=payload if isinstance(payload, dict) else {},
        )
