"""``ait init`` — interactive first-run setup wizard."""

from __future__ import annotations

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.text import Text

from ait_core.auth.api_key_store import APIKeyStore
from ait_core.auth.token_store import TokenStore

console = Console()

# Map of tool name → (display label, key-store service name, setup command hint)
_API_KEY_TOOLS: list[tuple[str, str, str]] = [
    ("xAI (Grok)",       "xai",       "ait-xai auth set-key"),
    ("Stripe",           "stripe",    "ait-stripe auth set-key"),
    ("SendGrid",         "sendgrid",  "ait-sendgrid auth set-key"),
    ("Resend",           "resend",    "ait-resend auth set-key"),
]

_SOCIAL_PLATFORMS: list[tuple[str, str]] = [
    ("Instagram",  "instagram"),
    ("Facebook",   "facebook"),
    ("Twitter/X",  "twitter"),
    ("LinkedIn",   "linkedin"),
    ("TikTok",     "tiktok"),
]

_GOOGLE_TOOLS: list[tuple[str, str]] = [
    ("Gmail",         "ait-gmail auth login"),
    ("Google Drive",  "ait-gdrive auth login"),
    ("Google Calendar", "ait-gcal auth login"),
]


def run_init() -> None:
    """Interactive setup wizard — walk user through every auth configuration.

    Args:
        None.

    Returns:
        None.

    Raises:
        typer.Exit: On user cancellation.
    """

    console.print(
        Panel(
            "[bold cyan]Welcome to AI Toolset![/bold cyan]\n\n"
            "This wizard will help you configure credentials for each tool.\n"
            "You can skip any tool and configure it later with its own auth command.",
            title="[bold]ait init[/bold]",
            border_style="cyan",
        )
    )

    key_store = APIKeyStore()
    token_store = TokenStore()

    # ── API-key tools ──────────────────────────────────────────────────────
    console.print("\n[bold]API Key Tools[/bold]")
    for label, service, hint in _API_KEY_TOOLS:
        existing = key_store.get_key(service)
        status = "[green]✓ configured[/green]" if existing else "[yellow]not set[/yellow]"
        console.print(f"  {label}: {status}")

        if Confirm.ask(f"  Configure {label} now?", default=not bool(existing)):
            key = Prompt.ask(f"  Enter your {label} API key", password=True)
            if key.strip():
                key_store.set_key(service, key.strip())
                console.print(f"  [green]✓ {label} key saved.[/green]")
            else:
                console.print(f"  [yellow]Skipped — run `{hint}` later.[/yellow]")

    # ── Social platforms ───────────────────────────────────────────────────
    console.print("\n[bold]Social Media Platforms[/bold]")
    for label, platform in _SOCIAL_PLATFORMS:
        service = f"social_{platform}"
        existing = key_store.get_key(service)
        status = "[green]✓ configured[/green]" if existing else "[yellow]not set[/yellow]"
        console.print(f"  {label}: {status}")

        if Confirm.ask(f"  Configure {label} access token now?", default=not bool(existing)):
            token = Prompt.ask(f"  Enter your {label} access token", password=True)
            if token.strip():
                key_store.set_key(service, token.strip())
                console.print(f"  [green]✓ {label} token saved.[/green]")
            else:
                console.print(
                    f"  [yellow]Skipped — run "
                    f"`ait-social auth set-token --platform {platform}` later.[/yellow]"
                )

    # ── Google OAuth tools ─────────────────────────────────────────────────
    console.print("\n[bold]Google OAuth Tools[/bold]")
    console.print(
        "  [dim]Google tools use a browser-based OAuth flow.\n"
        "  We'll show you the command to run for each.[/dim]"
    )
    for label, login_cmd in _GOOGLE_TOOLS:
        # Check TokenStore for any bundle with google_ prefix
        has_token = _has_google_token(token_store, label)
        status = "[green]✓ configured[/green]" if has_token else "[yellow]not set[/yellow]"
        console.print(f"  {label}: {status}")

        if not has_token:
            console.print(f"  [dim]→ Run: [bold]{login_cmd}[/bold][/dim]")

    # ── Summary ────────────────────────────────────────────────────────────
    console.print(
        Panel(
            _build_summary(key_store),
            title="[bold green]Setup Summary[/bold green]",
            border_style="green",
        )
    )
    console.print(
        "\n[dim]Run [bold]ait auth status[/bold] anytime to check your configuration.\n"
        "Run [bold]ait doctor[/bold] to diagnose connection issues.[/dim]\n"
    )


def _has_google_token(store: TokenStore, label: str) -> bool:
    """Heuristic check for any stored Google token bundle.

    Args:
        store: Token store instance.
        label: Tool label (unused — checks common scope fingerprints).

    Returns:
        True if at least one Google token bundle exists.

    Raises:
        None.
    """

    # GoogleAuthClient uses sha1-based keys; we probe the store's directory
    try:
        import os
        from pathlib import Path

        bundle_dir = Path(store._bundle_dir)  # type: ignore[attr-defined]
        if bundle_dir.exists():
            return any(f.startswith("google_") for f in os.listdir(bundle_dir))
    except Exception:  # noqa: BLE001
        pass
    return False


def _build_summary(key_store: APIKeyStore) -> Text:
    """Build a Rich Text summary of configured tools.

    Args:
        key_store: Loaded API key store.

    Returns:
        Formatted Rich Text object.

    Raises:
        None.
    """

    text = Text()
    all_services = (
        [("xAI", "xai"), ("Stripe", "stripe"), ("SendGrid", "sendgrid"), ("Resend", "resend")]
        + [(lbl, f"social_{p}") for lbl, p in _SOCIAL_PLATFORMS]
    )
    for label, service in all_services:
        configured = bool(key_store.get_key(service))
        icon = "✓" if configured else "✗"
        style = "green" if configured else "red"
        text.append(f"  {icon} {label}\n", style=style)
    return text
