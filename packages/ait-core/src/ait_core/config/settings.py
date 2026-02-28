"""Configuration loading and persistence for ai-toolset."""

from __future__ import annotations

import os
import tomllib
from pathlib import Path

import tomli_w
from pydantic import BaseModel, Field


class GeneralSettings(BaseModel):
    """Global CLI behavior settings."""

    output_format: str = "json"
    log_level: str = "warning"


class GoogleSettings(BaseModel):
    """Google OAuth configuration values."""

    client_id: str = ""
    client_secret: str = ""
    project_id: str = ""


class XAISettings(BaseModel):
    """xAI model and authentication settings."""

    api_key: str = ""
    default_model: str = "grok-3"
    image_model: str = "grok-2-image"


class ResendSettings(BaseModel):
    """Resend API settings."""

    api_key: str = ""
    default_from: str = ""


class SendGridSettings(BaseModel):
    """SendGrid API settings."""

    api_key: str = ""
    default_from: str = ""


class StripeSettings(BaseModel):
    """Stripe API settings."""

    api_key: str = ""
    stripe_version: str = "2024-06-20"


class SocialSettings(BaseModel):
    """Social tool defaults."""

    default_platform: str = "twitter"


class MemorySettings(BaseModel):
    """Local memory module settings."""

    db_path: str = "~/.ai-toolset/memory/memory.db"
    embedding_provider: str = "local"
    local_model: str = "all-MiniLM-L6-v2"
    max_search_results: int = 10


class AITSettings(BaseModel):
    """Top-level settings schema for `config.toml`."""

    general: GeneralSettings = Field(default_factory=GeneralSettings)
    google: GoogleSettings = Field(default_factory=GoogleSettings)
    xai: XAISettings = Field(default_factory=XAISettings)
    resend: ResendSettings = Field(default_factory=ResendSettings)
    sendgrid: SendGridSettings = Field(default_factory=SendGridSettings)
    stripe: StripeSettings = Field(default_factory=StripeSettings)
    social: SocialSettings = Field(default_factory=SocialSettings)
    memory: MemorySettings = Field(default_factory=MemorySettings)


def get_config_dir() -> Path:
    """Return config directory path.

    Args:
        None.

    Returns:
        Expanded directory path for ai-toolset config.

    Raises:
        None.
    """

    override = os.getenv("AIT_CONFIG_DIR")
    if override:
        return Path(override).expanduser().resolve()
    return Path("~/.ai-toolset").expanduser().resolve()


def get_config_path() -> Path:
    """Return path to `config.toml`.

    Args:
        None.

    Returns:
        Absolute path for the user config file.

    Raises:
        None.
    """

    return get_config_dir() / "config.toml"


def ensure_base_dirs(config_dir: Path | None = None) -> None:
    """Create required base directories for config/token/memory storage.

    Args:
        config_dir: Optional config root directory.

    Returns:
        None.

    Raises:
        OSError: If directories cannot be created.
    """

    root = config_dir or get_config_dir()
    (root / "tokens").mkdir(parents=True, exist_ok=True)
    (root / "memory").mkdir(parents=True, exist_ok=True)


def load_settings(config_path: Path | None = None) -> AITSettings:
    """Load settings from TOML or return defaults.

    Args:
        config_path: Optional explicit config path.

    Returns:
        Parsed settings object.

    Raises:
        tomllib.TOMLDecodeError: If config is malformed.
        OSError: If file read fails.
    """

    path = config_path or get_config_path()
    ensure_base_dirs(path.parent)
    if not path.exists():
        return AITSettings()

    data = tomllib.loads(path.read_text(encoding="utf-8"))
    return AITSettings.model_validate(data)


def save_settings(settings: AITSettings, config_path: Path | None = None) -> Path:
    """Persist settings to TOML.

    Args:
        settings: Settings object to serialize.
        config_path: Optional explicit destination path.

    Returns:
        Path where settings were saved.

    Raises:
        OSError: If write fails.
    """

    path = config_path or get_config_path()
    ensure_base_dirs(path.parent)
    payload = settings.model_dump(mode="json")
    path.write_text(tomli_w.dumps(payload), encoding="utf-8")
    return path
