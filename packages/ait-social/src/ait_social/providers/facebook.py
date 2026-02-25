"""Facebook Graph API provider."""

from __future__ import annotations

from ait_core.errors import ErrorCode, ExitCode, ToolsetError

from ait_social.models import SocialPostRequest, SocialPostResult, SocialProfileResult
from ait_social.providers.base import SocialProvider


class FacebookProvider(SocialProvider):
    """Facebook Page post and profile operations via Graph API."""

    platform = "facebook"
    base_url = "https://graph.facebook.com/v20.0"

    async def create_post(self, request: SocialPostRequest) -> SocialPostResult:
        """Create a Facebook page feed post."""

        if not request.account_id:
            raise ToolsetError(
                code=ErrorCode.INVALID_INPUT,
                message="Facebook posting requires --account-id (Page ID)",
                exit_code=ExitCode.INVALID_INPUT,
            )
        if not request.text and not request.link_url:
            raise ToolsetError(
                code=ErrorCode.INVALID_INPUT,
                message="Provide --text or --link-url for Facebook post",
                exit_code=ExitCode.INVALID_INPUT,
            )

        url = f"{self.base_url}/{request.account_id}/feed"
        params: dict[str, str] = {"access_token": self.access_token}
        if request.text:
            params["message"] = request.text
        if request.link_url:
            params["link"] = request.link_url

        response = await self._request("POST", url, params=params)
        self.raise_for_status(response, "Facebook")
        payload = response.json()
        post_id = payload.get("id") if isinstance(payload, dict) else None
        return SocialPostResult(
            platform="facebook",
            id=str(post_id) if post_id else None,
            status="published",
            raw=payload if isinstance(payload, dict) else {},
        )

    async def get_profile(self, account_id: str | None = None) -> SocialProfileResult:
        """Get Facebook page profile info."""

        if not account_id:
            raise ToolsetError(
                code=ErrorCode.INVALID_INPUT,
                message="Facebook profile lookup requires --account-id (Page ID)",
                exit_code=ExitCode.INVALID_INPUT,
            )

        url = f"{self.base_url}/{account_id}"
        response = await self._request(
            "GET",
            url,
            params={
                "fields": "id,name,fan_count",
                "access_token": self.access_token,
            },
        )
        self.raise_for_status(response, "Facebook")
        payload = response.json()
        followers = payload.get("fan_count") if isinstance(payload, dict) else None
        return SocialProfileResult(
            platform="facebook",
            account_id=str(payload.get("id")) if isinstance(payload, dict) else account_id,
            display_name=payload.get("name") if isinstance(payload, dict) else None,
            followers=int(followers) if isinstance(followers, int) else None,
            raw=payload if isinstance(payload, dict) else {},
        )
