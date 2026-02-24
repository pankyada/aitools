"""Tests for configuration persistence and loading."""

from __future__ import annotations

from pathlib import Path

from ait_core.config.settings import AITSettings, get_config_dir, load_settings, save_settings


def test_save_and_load_settings_roundtrip(tmp_path: Path) -> None:
    """Saved settings should load back identically."""

    path = tmp_path / "config.toml"
    settings = AITSettings()
    settings.google.client_id = "client-id"
    settings.google.client_secret = "client-secret"
    settings.xai.default_model = "grok-test"

    save_settings(settings, config_path=path)
    loaded = load_settings(config_path=path)

    assert loaded.google.client_id == "client-id"
    assert loaded.google.client_secret == "client-secret"
    assert loaded.xai.default_model == "grok-test"


def test_get_config_dir_from_env(monkeypatch: object, tmp_path: Path) -> None:
    """Environment override should control config path."""

    monkeypatch.setenv("AIT_CONFIG_DIR", str(tmp_path / "custom"))
    assert get_config_dir() == (tmp_path / "custom").resolve()
