"""Instagram Graph API provider."""

from __future__ import annotations

from ait_core.errors import ErrorCode, ExitCode, ToolsetError

from ait_social.models import SocialPostRequest, SocialPostResult, SocialProfileResult
from ait_social.providers.base import SocialProvider


class InstagramProvider(SocialProvider):
    """Instagram business posting provider via Graph API."""

    platform = "instagram"
    base_url = "https://graph.facebook.com/v20.0"

    async def create_post(self, request: SocialPostRequest) -> SocialPostResult:
        """Create and publish Instagram media post."""

        if not request.account_id:
            raise ToolsetError(
                code=ErrorCode.INVALID_INPUT,
                message="Instagram posting requires --account-id (IG User ID)",
                exit_code=ExitCode.INVALID_INPUT,
            )
        if not request.media_url:
            raise ToolsetError(
                code=ErrorCode.INVALID_INPUT,
                message="Instagram posting requires --media-url",
                exit_code=ExitCode.INVALID_INPUT,
            )

        create_url = f"{self.base_url}/{request.account_id}/media"
        create_params: dict[str, str] = {
            "access_token": self.access_token,
            "image_url": request.media_url,
        }
        if request.text:
            create_params["caption"] = request.text

        create_response = await self._request("POST", create_url, params=create_params)
        self.raise_for_status(create_response, "Instagram")
        create_payload = create_response.json()
        creation_id = create_payload.get("id") if isinstance(create_payload, dict) else None
        if not creation_id:
            raise ToolsetError(
                code=ErrorCode.GENERAL_ERROR,
                message="Instagram media creation did not return an id",
                exit_code=ExitCode.GENERAL_ERROR,
                details={"body": create_payload},
            )

        publish_url = f"{self.base_url}/{request.account_id}/media_publish"
        publish_response = await self._request(
            "POST",
            publish_url,
            params={
                "creation_id": str(creation_id),
                "access_token": self.access_token,
            },
        )
        self.raise_for_status(publish_response, "Instagram")
        publish_payload = publish_response.json()
        post_id = publish_payload.get("id") if isinstance(publish_payload, dict) else None

        return SocialPostResult(
            platform="instagram",
            id=str(post_id) if post_id else None,
            status="published",
            raw=publish_payload if isinstance(publish_payload, dict) else {},
        )

    async def get_profile(self, account_id: str | None = None) -> SocialProfileResult:
        """Get Instagram business profile data."""

        if not account_id:
            raise ToolsetError(
                code=ErrorCode.INVALID_INPUT,
                message="Instagram profile lookup requires --account-id (IG User ID)",
                exit_code=ExitCode.INVALID_INPUT,
            )

        url = f"{self.base_url}/{account_id}"
        response = await self._request(
            "GET",
            url,
            params={
                "fields": "id,username,followers_count,media_count",
                "access_token": self.access_token,
            },
        )
        self.raise_for_status(response, "Instagram")
        payload = response.json()
        followers = payload.get("followers_count") if isinstance(payload, dict) else None
        return SocialProfileResult(
            platform="instagram",
            account_id=str(payload.get("id")) if isinstance(payload, dict) else account_id,
            username=payload.get("username") if isinstance(payload, dict) else None,
            followers=int(followers) if isinstance(followers, int) else None,
            raw=payload if isinstance(payload, dict) else {},
        )
