"""``ait auth status`` — consolidated auth dashboard."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.table import Table

from ait_core.auth.api_key_store import APIKeyStore
from ait_core.auth.token_store import TokenStore

console = Console()

_API_KEY_SERVICES: list[tuple[str, str, str]] = [
    ("xAI",            "xai",           "ait-xai auth set-key"),
    ("Stripe",         "stripe",        "ait-stripe auth set-key"),
    ("SendGrid",       "sendgrid",      "ait-sendgrid auth set-key"),
    ("Resend",         "resend",        "ait-resend auth set-key"),
    ("Instagram",      "social_instagram", "ait-social auth set-token --platform instagram"),
    ("Facebook",       "social_facebook",  "ait-social auth set-token --platform facebook"),
    ("Twitter/X",      "social_twitter",   "ait-social auth set-token --platform twitter"),
    ("LinkedIn",       "social_linkedin",  "ait-social auth set-token --platform linkedin"),
    ("TikTok",         "social_tiktok",    "ait-social auth set-token --platform tiktok"),
]


def run_auth_status() -> None:
    """Render a Rich table showing auth status for every configured tool.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    key_store = APIKeyStore()
    token_store = TokenStore()

    table = Table(
        title="AI Toolset — Auth Status",
        show_header=True,
        header_style="bold cyan",
        border_style="dim",
        expand=True,
    )
    table.add_column("Tool", style="bold", min_width=16)
    table.add_column("Auth Type", style="dim", min_width=10)
    table.add_column("Status", min_width=14)
    table.add_column("Details / Fix", style="dim")

    # ── API-key tools ──────────────────────────────────────────────────────
    for label, service, fix_cmd in _API_KEY_SERVICES:
        key = key_store.get_key(service)
        if key:
            status = "[green]✓  configured[/green]"
            detail = f"key stored ({len(key)} chars)"
        else:
            status = "[red]✗  missing[/red]"
            detail = f"[dim]{fix_cmd}[/dim]"
        table.add_row(label, "API key", status, detail)

    # ── Google OAuth tools ─────────────────────────────────────────────────
    google_tools = [
        ("Gmail",           "ait-gmail auth login"),
        ("Google Drive",    "ait-gdrive auth login"),
        ("Google Calendar", "ait-gcal auth login"),
    ]
    bundles = _load_google_bundles(token_store)

    for label, login_cmd in google_tools:
        if bundles:
            # Pick the most-recently-stored bundle as representative
            bundle = next(iter(bundles.values()))
            status_str, detail = _google_bundle_status(bundle, login_cmd)
        else:
            status_str = "[red]✗  not logged in[/red]"
            detail = f"[dim]{login_cmd}[/dim]"
        table.add_row(label, "Google OAuth", status_str, detail)

    console.print()
    console.print(table)
    console.print(
        "\n[dim]Run [bold]ait init[/bold] for guided setup  •  "
        "[bold]ait doctor[/bold] to diagnose connectivity issues[/dim]\n"
    )


# ── helpers ───────────────────────────────────────────────────────────────────


def _load_google_bundles(store: TokenStore) -> dict[str, dict[str, Any]]:
    """Load all Google token bundles from the token store directory.

    Args:
        store: Token store instance.

    Returns:
        Mapping of bundle key → bundle dict for entries with ``google_`` prefix.

    Raises:
        None.
    """

    bundles: dict[str, dict[str, Any]] = {}
    try:
        bundle_dir = Path(store._bundle_dir)  # type: ignore[attr-defined]
        if not bundle_dir.exists():
            return bundles
        for name in os.listdir(bundle_dir):
            if name.startswith("google_"):
                key = name
                bundle = store.load_token_bundle(key)
                if bundle is not None:
                    bundles[key] = bundle
    except Exception:  # noqa: BLE001
        pass
    return bundles


def _google_bundle_status(bundle: dict[str, Any], login_cmd: str) -> tuple[str, str]:
    """Derive status string and detail text from a Google token bundle.

    Args:
        bundle: Stored token bundle dict.
        login_cmd: Login command hint to show when expired/invalid.

    Returns:
        ``(status_markup, detail_text)`` tuple.

    Raises:
        None.
    """

    expires_at_raw = bundle.get("expires_at")
    if not isinstance(expires_at_raw, str):
        return "[yellow]⚠  invalid token[/yellow]", f"[dim]{login_cmd}[/dim]"

    try:
        expires_at = datetime.fromisoformat(expires_at_raw)
        if expires_at.tzinfo is None:
            expires_at = expires_at.replace(tzinfo=UTC)
    except ValueError:
        return "[yellow]⚠  invalid token[/yellow]", f"[dim]{login_cmd}[/dim]"

    now = datetime.now(tz=UTC)
    if now >= expires_at:
        return (
            "[red]✗  expired[/red]",
            f"[dim]{login_cmd}[/dim] (token expired {expires_at.strftime('%Y-%m-%d')})",
        )

    scope = bundle.get("scope", "")
    scopes_short = ", ".join(scope.split()) if scope else "—"
    return (
        "[green]✓  active[/green]",
        f"expires {expires_at.strftime('%Y-%m-%d %H:%M')} UTC  •  {scopes_short[:60]}",
    )
