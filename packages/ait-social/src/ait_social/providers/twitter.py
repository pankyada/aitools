"""Twitter/X API provider."""

from __future__ import annotations

from ait_core.errors import ErrorCode, ExitCode, ToolsetError

from ait_social.models import SocialPostRequest, SocialPostResult, SocialProfileResult
from ait_social.providers.base import SocialProvider


class TwitterProvider(SocialProvider):
    """Twitter/X provider for simple tweet and profile operations."""

    platform = "twitter"
    base_url = "https://api.twitter.com/2"

    def _headers(self) -> dict[str, str]:
        """Build bearer auth headers."""

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }

    async def create_post(self, request: SocialPostRequest) -> SocialPostResult:
        """Create tweet post."""

        if not request.text:
            raise ToolsetError(
                code=ErrorCode.INVALID_INPUT,
                message="Twitter posting requires --text",
                exit_code=ExitCode.INVALID_INPUT,
            )

        response = await self._request(
            "POST",
            f"{self.base_url}/tweets",
            headers=self._headers(),
            json={"text": request.text},
        )
        self.raise_for_status(response, "Twitter")
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else {}
        tweet_id = data.get("id") if isinstance(data, dict) else None
        return SocialPostResult(
            platform="twitter",
            id=str(tweet_id) if tweet_id else None,
            status="published",
            url=f"https://x.com/i/web/status/{tweet_id}" if tweet_id else None,
            raw=payload if isinstance(payload, dict) else {},
        )

    async def get_profile(self, account_id: str | None = None) -> SocialProfileResult:
        """Get authenticated account profile info."""

        response = await self._request(
            "GET",
            f"{self.base_url}/users/me",
            headers=self._headers(),
            params={"user.fields": "public_metrics,username,name,verified"},
        )
        self.raise_for_status(response, "Twitter")
        payload = response.json()
        data = payload.get("data") if isinstance(payload, dict) else {}
        metrics = data.get("public_metrics") if isinstance(data, dict) else {}
        followers = metrics.get("followers_count") if isinstance(metrics, dict) else None
        return SocialProfileResult(
            platform="twitter",
            account_id=str(data.get("id")) if isinstance(data, dict) else account_id,
            display_name=data.get("name") if isinstance(data, dict) else None,
            username=data.get("username") if isinstance(data, dict) else None,
            followers=int(followers) if isinstance(followers, int) else None,
            raw=payload if isinstance(payload, dict) else {},
        )
