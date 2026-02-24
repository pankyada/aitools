"""Encrypted API-key storage helper."""

from __future__ import annotations

from typing import Any

from ait_core.auth.token_store import TokenStore


class APIKeyStore:
    """Store API keys in encrypted storage.

    Args:
        token_store: Optional injected token store.

    Returns:
        None.

    Raises:
        None.
    """

    _BUNDLE_NAME = "api_keys"

    def __init__(self, token_store: TokenStore | None = None) -> None:
        self.token_store = token_store or TokenStore()

    def set_key(self, service: str, value: str) -> None:
        """Persist an API key for a service.

        Args:
            service: Service name, such as `xai`.
            value: Secret API key value.

        Returns:
            None.

        Raises:
            OSError: If storage write fails.
        """

        bundle = self.token_store.load_token_bundle(self._BUNDLE_NAME) or {}
        bundle[service] = value
        self.token_store.save_token_bundle(self._BUNDLE_NAME, bundle)

    def get_key(self, service: str) -> str | None:
        """Retrieve an API key by service.

        Args:
            service: Service key name.

        Returns:
            The stored key or None.

        Raises:
            OSError: If storage read fails.
        """

        bundle = self.token_store.load_token_bundle(self._BUNDLE_NAME) or {}
        value: Any = bundle.get(service)
        if value is None:
            return None
        if not isinstance(value, str):
            return None
        return value

    def delete_key(self, service: str) -> bool:
        """Delete API key for a service.

        Args:
            service: Service key name.

        Returns:
            True if key existed and was deleted.

        Raises:
            OSError: If storage write fails.
        """

        bundle = self.token_store.load_token_bundle(self._BUNDLE_NAME) or {}
        if service not in bundle:
            return False
        del bundle[service]
        self.token_store.save_token_bundle(self._BUNDLE_NAME, bundle)
        return True

    @staticmethod
    def mask_value(value: str) -> str:
        """Return masked preview of a secret key.

        Args:
            value: Full key value.

        Returns:
            Masked preview for status output.

        Raises:
            None.
        """

        if len(value) <= 8:
            return "*" * len(value)
        return f"{value[:4]}...{value[-4:]}"
