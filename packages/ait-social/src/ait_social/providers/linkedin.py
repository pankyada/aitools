"""LinkedIn API provider."""

from __future__ import annotations

from ait_core.errors import ErrorCode, ExitCode, ToolsetError

from ait_social.models import SocialPostRequest, SocialPostResult, SocialProfileResult
from ait_social.providers.base import SocialProvider


class LinkedInProvider(SocialProvider):
    """LinkedIn provider using UGC Posts and profile endpoints."""

    platform = "linkedin"
    base_url = "https://api.linkedin.com/v2"

    def _headers(self) -> dict[str, str]:
        """Build bearer auth headers."""

        return {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
            "X-Restli-Protocol-Version": "2.0.0",
        }

    async def create_post(self, request: SocialPostRequest) -> SocialPostResult:
        """Create a LinkedIn UGC post."""

        if not request.account_id:
            raise ToolsetError(
                code=ErrorCode.INVALID_INPUT,
                message="LinkedIn posting requires --account-id (author URN)",
                exit_code=ExitCode.INVALID_INPUT,
            )
        if not request.text:
            raise ToolsetError(
                code=ErrorCode.INVALID_INPUT,
                message="LinkedIn posting requires --text",
                exit_code=ExitCode.INVALID_INPUT,
            )

        body = {
            "author": request.account_id,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": request.text},
                    "shareMediaCategory": "NONE",
                }
            },
            "visibility": {
                "com.linkedin.ugc.MemberNetworkVisibility": request.visibility or "PUBLIC"
            },
        }

        response = await self._request(
            "POST",
            f"{self.base_url}/ugcPosts",
            headers=self._headers(),
            json=body,
        )
        self.raise_for_status(response, "LinkedIn")
        post_urn = response.headers.get("x-restli-id")
        payload = {"headers": dict(response.headers)}
        return SocialPostResult(
            platform="linkedin",
            id=post_urn,
            status="published",
            raw=payload,
        )

    async def get_profile(self, account_id: str | None = None) -> SocialProfileResult:
        """Get LinkedIn profile for authenticated user."""

        _ = account_id
        response = await self._request(
            "GET",
            f"{self.base_url}/me",
            headers=self._headers(),
        )
        self.raise_for_status(response, "LinkedIn")
        payload = response.json()
        first_name = ""
        last_name = ""
        if isinstance(payload, dict):
            fn = payload.get("localizedFirstName")
            ln = payload.get("localizedLastName")
            first_name = fn if isinstance(fn, str) else ""
            last_name = ln if isinstance(ln, str) else ""
        display = f"{first_name} {last_name}".strip() or None
        account = str(payload.get("id")) if isinstance(payload, dict) else None
        return SocialProfileResult(
            platform="linkedin",
            account_id=account,
            display_name=display,
            raw=payload if isinstance(payload, dict) else {},
        )
