"""xAI REST client wrapper."""

from __future__ import annotations

import base64
from pathlib import Path
from typing import Any

import httpx
from ait_core.auth.api_key_store import APIKeyStore
from ait_core.config.settings import AITSettings
from ait_core.errors import ErrorCode, ExitCode, ToolsetError
from ait_core.http.retry import request_with_retry

from ait_xai.models import (
    ChatMessage,
    ChatRequest,
    ChatResult,
    ImageRequest,
    ImageResult,
    VideoRequest,
    VideoResult,
)

BASE_URL = "https://api.x.ai/v1"


class XAIClient:
    """Client for xAI chat, image, and video endpoints.

    Args:
        settings: Loaded ai-toolset settings.
        api_key_store: Optional API key storage abstraction.
        http_client: Optional async HTTP client.

    Returns:
        None.

    Raises:
        ToolsetError: If API key is missing.
    """

    def __init__(
        self,
        settings: AITSettings,
        api_key_store: APIKeyStore | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self.api_key_store = api_key_store or APIKeyStore()
        self.client = http_client or httpx.AsyncClient(timeout=60)

        api_key = self.settings.xai.api_key or self.api_key_store.get_key("xai")
        if not api_key:
            raise ToolsetError(
                code=ErrorCode.AUTH_ERROR,
                message="xAI API key is not configured",
                exit_code=ExitCode.AUTH_ERROR,
                recovery_hints=[
                    "Run: ait-xai auth set-key",
                    "Or set xai.api_key in settings.toml",
                    "Get your key at: https://console.x.ai",
                ],
            )
        self.api_key = api_key

    def _headers(self) -> dict[str, str]:
        """Build authorization headers.

        Args:
            None.

        Returns:
            Header dictionary with bearer auth.

        Raises:
            None.
        """

        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

    async def verify_auth(self) -> bool:
        """Verify API key by issuing a minimal chat request.

        Args:
            None.

        Returns:
            True if key is valid.

        Raises:
            ToolsetError: If request fails or key is invalid.
        """

        req = ChatRequest(
            model=self.settings.xai.default_model,
            messages=[ChatMessage(role="user", content="ping")],
            max_tokens=1,
            temperature=0.0,
            stream=False,
        )
        await self.chat(req)
        return True

    async def chat(self, request: ChatRequest) -> ChatResult:
        """Create a chat completion response.

        Args:
            request: Chat completion request payload.

        Returns:
            Normalized chat result.

        Raises:
            ToolsetError: If API request fails.
        """

        response = await request_with_retry(
            self.client,
            "POST",
            f"{BASE_URL}/chat/completions",
            headers=self._headers(),
            json=request.model_dump(exclude_none=True),
        )

        if response.status_code >= 400:
            self._raise_http_error(response)

        data = response.json()
        try:
            choice = data["choices"][0]
            content = choice["message"]["content"]
            finish_reason = choice.get("finish_reason")
            model = data.get("model", request.model)
        except (KeyError, IndexError, TypeError) as exc:
            raise ToolsetError(
                code=ErrorCode.GENERAL_ERROR,
                message="Unexpected xAI chat response format",
                exit_code=ExitCode.GENERAL_ERROR,
                details={"response": data},
            ) from exc

        return ChatResult(model=model, content=content, finish_reason=finish_reason)

    async def generate_image(self, request: ImageRequest) -> ImageResult:
        """Generate images from a prompt.

        Args:
            request: Image generation request.

        Returns:
            Normalized image result including b64 strings or URLs.

        Raises:
            ToolsetError: If API request fails.
        """

        response = await request_with_retry(
            self.client,
            "POST",
            f"{BASE_URL}/images/generations",
            headers=self._headers(),
            json=request.model_dump(exclude_none=True),
        )
        if response.status_code >= 400:
            self._raise_http_error(response)

        data = response.json()
        images: list[str] = []
        for item in data.get("data", []):
            if "b64_json" in item:
                images.append(item["b64_json"])
            elif "url" in item:
                images.append(item["url"])

        return ImageResult(created=data.get("created"), images=images)

    async def generate_video(self, request: VideoRequest) -> VideoResult:
        """Submit a video generation request.

        Args:
            request: Video generation request payload.

        Returns:
            Normalized video generation response.

        Raises:
            ToolsetError: If API request fails.
        """

        response = await request_with_retry(
            self.client,
            "POST",
            f"{BASE_URL}/videos/generations",
            headers=self._headers(),
            json=request.model_dump(exclude_none=True),
        )
        if response.status_code >= 400:
            self._raise_http_error(response)

        data = response.json()
        return VideoResult(
            id=data.get("id"),
            status=data.get("status"),
            output_url=data.get("output_url") or data.get("url"),
        )

    async def save_image_payload(self, image_payload: str, output: Path) -> Path:
        """Save base64 payload or URL content to disk.

        Args:
            image_payload: Base64 string or URL.
            output: Destination path.

        Returns:
            Output path where image bytes were written.

        Raises:
            ToolsetError: If download/decoding fails.
        """

        output.parent.mkdir(parents=True, exist_ok=True)
        if image_payload.startswith("http://") or image_payload.startswith("https://"):
            response = await request_with_retry(self.client, "GET", image_payload)
            if response.status_code >= 400:
                self._raise_http_error(response)
            output.write_bytes(response.content)
            return output

        try:
            output.write_bytes(base64.b64decode(image_payload))
        except ValueError as exc:
            raise ToolsetError(
                code=ErrorCode.GENERAL_ERROR,
                message="Image payload was neither URL nor valid base64",
                exit_code=ExitCode.GENERAL_ERROR,
            ) from exc
        return output

    def _raise_http_error(self, response: httpx.Response) -> None:
        """Raise typed tool error from an HTTP response.

        Args:
            response: HTTP response with error status.

        Returns:
            None.

        Raises:
            ToolsetError: Always raised.
        """

        code = ErrorCode.GENERAL_ERROR
        exit_code = ExitCode.GENERAL_ERROR
        hints: list[str] | None = None
        if response.status_code in {401, 403}:
            code = ErrorCode.AUTH_ERROR
            exit_code = ExitCode.AUTH_ERROR
            hints = [
                "Your xAI API key may be invalid or revoked",
                "Run: ait-xai auth set-key  to update it",
                "Check your keys at: https://console.x.ai",
            ]
        elif response.status_code == 404:
            code = ErrorCode.NOT_FOUND
            exit_code = ExitCode.NOT_FOUND
        elif response.status_code == 429:
            code = ErrorCode.RATE_LIMITED
            exit_code = ExitCode.RATE_LIMITED

        body: Any
        try:
            body = response.json()
        except ValueError:
            body = response.text

        raise ToolsetError(
            code=code,
            message=f"xAI API request failed ({response.status_code})",
            exit_code=exit_code,
            details={"body": body},
            recovery_hints=hints,
        )
