"""``ait doctor`` — diagnostics and health checks."""

from __future__ import annotations

import asyncio
import importlib
import sys
from typing import Any

import httpx
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ait_core.auth.api_key_store import APIKeyStore
from ait_core.auth.token_store import TokenStore

console = Console()

# (check label, target URL)
_CONNECTIVITY_CHECKS: list[tuple[str, str]] = [
    ("Google OAuth",  "https://oauth2.googleapis.com"),
    ("xAI API",       "https://api.x.ai"),
    ("Stripe API",    "https://api.stripe.com"),
    ("SendGrid API",  "https://api.sendgrid.com"),
    ("Resend API",    "https://api.resend.com"),
]

# (label, importable package)
_PACKAGE_CHECKS: list[tuple[str, str]] = [
    ("ait-core",     "ait_core"),
    ("ait-gmail",    "ait_gmail"),
    ("ait-gdrive",   "ait_gdrive"),
    ("ait-gcal",     "ait_gcal"),
    ("ait-xai",      "ait_xai"),
    ("ait-memory",   "ait_memory"),
    ("ait-resend",   "ait_resend"),
    ("ait-sendgrid", "ait_sendgrid"),
    ("ait-social",   "ait_social"),
    ("ait-stripe",   "ait_stripe"),
]

# (label, service key)
_AUTH_CHECKS: list[tuple[str, str]] = [
    ("xAI",       "xai"),
    ("Stripe",    "stripe"),
    ("SendGrid",  "sendgrid"),
    ("Resend",    "resend"),
]


def run_doctor() -> None:
    """Run full diagnostics suite and print Rich-formatted results.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    console.print(
        Panel(
            "[bold]Running diagnostics…[/bold]",
            title="[bold cyan]ait doctor[/bold cyan]",
            border_style="cyan",
        )
    )

    issues: list[str] = []

    # ── Python version ─────────────────────────────────────────────────────
    py_ok = sys.version_info >= (3, 11)
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    _print_check(
        "Python version",
        py_ok,
        f"{py_ver} {'✓' if py_ok else '(need ≥ 3.11)'}",
    )
    if not py_ok:
        issues.append(f"Python {py_ver} is below the required 3.11 minimum")

    # ── Package availability ───────────────────────────────────────────────
    console.print("\n[bold]Package availability[/bold]")
    pkg_table = _build_pkg_table()
    console.print(pkg_table)

    for label, pkg in _PACKAGE_CHECKS:
        try:
            importlib.import_module(pkg)
        except ImportError:
            issues.append(f"{label} is not importable — run: uv sync")

    # ── API key auth ───────────────────────────────────────────────────────
    console.print("\n[bold]API key configuration[/bold]")
    key_store = APIKeyStore()
    _token_store = TokenStore()
    auth_table = _build_auth_table(key_store)
    console.print(auth_table)

    for label, service in _AUTH_CHECKS:
        if not key_store.get_key(service):
            issues.append(
                f"{label} API key not configured — run: ait-{service} auth set-key"
            )

    # ── Network connectivity ───────────────────────────────────────────────
    console.print("\n[bold]Network connectivity[/bold]")
    net_results = asyncio.run(_run_connectivity_checks())
    net_table = _build_net_table(net_results)
    console.print(net_table)

    for label, _url, ok, detail in net_results:
        if not ok:
            issues.append(f"Cannot reach {label}: {detail}")

    # ── Final verdict ──────────────────────────────────────────────────────
    console.print()
    if not issues:
        console.print(
            Panel(
                "[bold green]✓ All checks passed — your setup looks healthy![/bold green]",
                border_style="green",
            )
        )
    else:
        body = Text()
        body.append(f"Found {len(issues)} issue(s):\n\n", style="bold red")
        for i, issue in enumerate(issues, 1):
            body.append(f"  {i}. {issue}\n", style="red")
        body.append("\n[dim]Run [bold]ait init[/bold] to fix auth issues.[/dim]")
        console.print(Panel(body, title="[bold red]Issues Found[/bold red]", border_style="red"))


# ── table builders ─────────────────────────────────────────────────────────────


def _build_pkg_table() -> Table:
    """Build Rich table for package availability checks.

    Args:
        None.

    Returns:
        Populated Rich Table.

    Raises:
        None.
    """

    table = Table(show_header=True, header_style="bold", border_style="dim")
    table.add_column("Package", min_width=16)
    table.add_column("Status", min_width=14)

    for label, pkg in _PACKAGE_CHECKS:
        try:
            importlib.import_module(pkg)
            status = "[green]✓  installed[/green]"
        except ImportError:
            status = "[red]✗  not found[/red]"
        table.add_row(label, status)
    return table


def _build_auth_table(key_store: APIKeyStore) -> Table:
    """Build Rich table for API-key auth status.

    Args:
        key_store: Loaded API key store.

    Returns:
        Populated Rich Table.

    Raises:
        None.
    """

    table = Table(show_header=True, header_style="bold", border_style="dim")
    table.add_column("Service", min_width=14)
    table.add_column("Status", min_width=14)
    table.add_column("Fix", style="dim")

    services = [
        ("xAI",       "xai",       "ait-xai auth set-key"),
        ("Stripe",    "stripe",    "ait-stripe auth set-key"),
        ("SendGrid",  "sendgrid",  "ait-sendgrid auth set-key"),
        ("Resend",    "resend",    "ait-resend auth set-key"),
    ]
    for label, service, fix in services:
        key = key_store.get_key(service)
        if key:
            table.add_row(label, "[green]✓  configured[/green]", "")
        else:
            table.add_row(label, "[red]✗  missing[/red]", fix)
    return table


def _build_net_table(results: list[tuple[str, str, bool, str]]) -> Table:
    """Build Rich table for network connectivity results.

    Args:
        results: List of ``(label, url, ok, detail)`` tuples.

    Returns:
        Populated Rich Table.

    Raises:
        None.
    """

    table = Table(show_header=True, header_style="bold", border_style="dim")
    table.add_column("Service", min_width=16)
    table.add_column("URL", style="dim", min_width=30)
    table.add_column("Status", min_width=14)
    table.add_column("Detail", style="dim")

    for label, url, ok, detail in results:
        status = "[green]✓  reachable[/green]" if ok else "[red]✗  unreachable[/red]"
        table.add_row(label, url, status, detail)
    return table


def _print_check(label: str, ok: bool, detail: str) -> None:
    """Print a single inline check result.

    Args:
        label: Check label.
        ok: Whether the check passed.
        detail: Detail string.

    Returns:
        None.

    Raises:
        None.
    """

    icon = "[green]✓[/green]" if ok else "[red]✗[/red]"
    console.print(f"  {icon}  {label}: {detail}")


# ── async connectivity ─────────────────────────────────────────────────────────


async def _run_connectivity_checks() -> list[tuple[str, str, bool, str]]:
    """Probe each target URL with a HEAD request.

    Args:
        None.

    Returns:
        List of ``(label, url, ok, detail)`` tuples.

    Raises:
        None.
    """

    results: list[tuple[str, str, bool, str]] = []
    async with httpx.AsyncClient(timeout=10) as client:
        tasks = [_probe(client, label, url) for label, url in _CONNECTIVITY_CHECKS]
        results = list(await asyncio.gather(*tasks))
    return results


async def _probe(
    client: httpx.AsyncClient, label: str, url: str
) -> tuple[str, str, bool, str]:
    """Probe a single URL.

    Args:
        client: Shared HTTP client.
        label: Check label.
        url: Target URL.

    Returns:
        ``(label, url, ok, detail)`` tuple.

    Raises:
        None.
    """

    try:
        response = await client.head(url, follow_redirects=True)
        return (label, url, True, f"HTTP {response.status_code}")
    except httpx.TimeoutException:
        return (label, url, False, "timed out (10s)")
    except httpx.ConnectError as exc:
        return (label, url, False, str(exc)[:60])
    except Exception as exc:  # noqa: BLE001
        return (label, url, False, str(exc)[:60])
