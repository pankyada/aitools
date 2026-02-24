"""Embedding generation with local and xAI providers."""

from __future__ import annotations

import hashlib
import math
from typing import Any

import httpx
from ait_core.auth.api_key_store import APIKeyStore
from ait_core.config.settings import AITSettings
from ait_core.errors import ErrorCode, ExitCode, ToolsetError
from ait_core.http.retry import request_with_retry

EMBED_DIM = 384


class EmbeddingProvider:
    """Embedding provider with local and xAI backends.

    Args:
        settings: Loaded settings.

    Returns:
        None.

    Raises:
        None.
    """

    def __init__(self, settings: AITSettings) -> None:
        self.settings = settings
        self._local_model: Any = None

    async def embed(self, text: str) -> list[float]:
        """Create an embedding vector.

        Args:
            text: Input text.

        Returns:
            Dense embedding list.

        Raises:
            ToolsetError: If xAI embedding call fails.
        """

        provider = self.settings.memory.embedding_provider
        if provider == "xai":
            return await self._embed_xai(text)
        return self._embed_local(text)

    def _embed_local(self, text: str) -> list[float]:
        """Generate local embedding using sentence-transformers or fallback hash.

        Args:
            text: Input text.

        Returns:
            Dense embedding list.

        Raises:
            None.
        """

        try:
            if self._local_model is None:
                from sentence_transformers import SentenceTransformer

                self._local_model = SentenceTransformer(self.settings.memory.local_model)
            vector = self._local_model.encode([text])[0]
            return [float(v) for v in vector.tolist()]
        except Exception:
            digest = hashlib.sha512(text.encode("utf-8")).digest()
            values: list[float] = []
            for index in range(EMBED_DIM):
                byte = digest[index % len(digest)]
                normalized = (byte / 255.0) * 2.0 - 1.0
                values.append(normalized)
            norm = math.sqrt(sum(v * v for v in values)) or 1.0
            return [v / norm for v in values]

    async def _embed_xai(self, text: str) -> list[float]:
        """Generate embedding via xAI API.

        Args:
            text: Input text.

        Returns:
            Dense embedding list.

        Raises:
            ToolsetError: If API key missing or request fails.
        """

        api_key = self.settings.xai.api_key or APIKeyStore().get_key("xai")
        if not api_key:
            raise ToolsetError(
                code=ErrorCode.AUTH_ERROR,
                message="xAI API key not configured for embeddings",
                exit_code=ExitCode.AUTH_ERROR,
            )

        async with httpx.AsyncClient(timeout=45) as client:
            response = await request_with_retry(
                client,
                "POST",
                "https://api.x.ai/v1/embeddings",
                headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
                json={"model": "grok-embedding", "input": text},
            )

        if response.status_code >= 400:
            raise ToolsetError(
                code=ErrorCode.GENERAL_ERROR,
                message=f"xAI embeddings request failed ({response.status_code})",
                exit_code=ExitCode.GENERAL_ERROR,
                details={"body": response.text},
            )

        body = response.json()
        data = body.get("data", [])
        if not data:
            raise ToolsetError(
                code=ErrorCode.GENERAL_ERROR,
                message="xAI embeddings response missing data",
                exit_code=ExitCode.GENERAL_ERROR,
            )
        vector = data[0].get("embedding", [])
        return [float(v) for v in vector]
