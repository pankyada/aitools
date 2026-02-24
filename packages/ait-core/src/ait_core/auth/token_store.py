"""Encrypted token persistence helpers."""

from __future__ import annotations

import base64
import hashlib
import json
import os
import platform
from pathlib import Path
from typing import Any

from cryptography.fernet import Fernet

from ait_core.config.settings import get_config_dir


class TokenStore:
    """Encrypted token storage for OAuth and other credentials.

    Args:
        root_dir: Optional config root override.

    Returns:
        None.

    Raises:
        OSError: If storage files cannot be created.
    """

    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = root_dir or get_config_dir()
        self.tokens_dir = self.root_dir / "tokens"
        self.tokens_dir.mkdir(parents=True, exist_ok=True)
        self._salt_path = self.tokens_dir / ".salt"
        self._fernet = Fernet(self._derive_key())

    def _derive_key(self) -> bytes:
        """Derive a Fernet key from machine context plus optional password.

        Args:
            None.

        Returns:
            URL-safe base64 key bytes suitable for Fernet.

        Raises:
            OSError: If salt read/write fails.
        """

        if self._salt_path.exists():
            salt = self._salt_path.read_bytes()
        else:
            salt = os.urandom(16)
            self._salt_path.write_bytes(salt)

        password = os.getenv("AIT_TOKEN_PASSWORD", "")
        seed = f"{platform.node()}::{password}".encode()
        digest = hashlib.pbkdf2_hmac("sha256", seed, salt, 390_000, dklen=32)
        return base64.urlsafe_b64encode(digest)

    def _path_for(self, name: str) -> Path:
        """Return encrypted token filename for logical key.

        Args:
            name: Logical token name.

        Returns:
            Full path for the encrypted token bundle.

        Raises:
            None.
        """

        safe_name = name.replace("/", "_")
        return self.tokens_dir / f"{safe_name}.json"

    def save_token_bundle(self, name: str, payload: dict[str, Any]) -> Path:
        """Encrypt and save token data.

        Args:
            name: Logical token key.
            payload: JSON-serializable token payload.

        Returns:
            Path where encrypted payload was persisted.

        Raises:
            TypeError: If payload is not JSON serializable.
            OSError: If write fails.
        """

        encoded = json.dumps(payload).encode("utf-8")
        encrypted = self._fernet.encrypt(encoded)
        path = self._path_for(name)
        path.write_bytes(encrypted)
        return path

    def load_token_bundle(self, name: str) -> dict[str, Any] | None:
        """Load and decrypt a token bundle if present.

        Args:
            name: Logical token key.

        Returns:
            Decrypted payload, or None if absent.

        Raises:
            ValueError: If payload is corrupted or cannot be decoded.
            OSError: If read fails.
        """

        path = self._path_for(name)
        if not path.exists():
            return None

        decrypted = self._fernet.decrypt(path.read_bytes())
        loaded: Any = json.loads(decrypted.decode("utf-8"))
        if not isinstance(loaded, dict):
            raise ValueError("Token bundle payload is not an object")
        return loaded

    def delete_token_bundle(self, name: str) -> bool:
        """Delete an encrypted token bundle if it exists.

        Args:
            name: Logical token key.

        Returns:
            True when deleted; False when absent.

        Raises:
            OSError: If delete fails.
        """

        path = self._path_for(name)
        if not path.exists():
            return False
        path.unlink()
        return True
