"""Root Typer application for the ``ait`` unified umbrella CLI."""

from __future__ import annotations

from importlib.metadata import version as pkg_version
from typing import Annotated, Optional

import typer
from rich.console import Console

from ait_cli.commands.auth import run_auth_status
from ait_cli.commands.doctor import run_doctor
from ait_cli.commands.init import run_init
from ait_cli.discovery import discover_tool_apps

console = Console()

# ── Root app ───────────────────────────────────────────────────────────────────

app = typer.Typer(
    name="ait",
    help=(
        "AI Toolset — unified command-line interface.\n\n"
        "Run [bold]ait init[/bold] to get started, "
        "[bold]ait auth status[/bold] to check credentials, "
        "or [bold]ait doctor[/bold] to diagnose issues."
    ),
    no_args_is_help=True,
    rich_markup_mode="rich",
    add_completion=True,
    pretty_exceptions_enable=False,
)

# ── auth sub-app ───────────────────────────────────────────────────────────────

auth_app = typer.Typer(
    name="auth",
    help="Auth management — view and verify credentials for all tools.",
    no_args_is_help=True,
    rich_markup_mode="rich",
    pretty_exceptions_enable=False,
)
app.add_typer(auth_app, name="auth")


@auth_app.command("status")
def auth_status() -> None:
    """Show auth status for every configured tool.

    Args:
        None (reads from APIKeyStore and TokenStore).

    Returns:
        None.

    Raises:
        None.
    """

    run_auth_status()


# ── top-level commands ─────────────────────────────────────────────────────────


@app.command("init")
def init() -> None:
    """Interactive first-run setup wizard.

    Walk through every tool and configure credentials.
    You can skip any step and re-run later.

    Args:
        None.

    Returns:
        None.

    Raises:
        typer.Exit: On user cancellation.
    """

    run_init()


@app.command("doctor")
def doctor() -> None:
    """Run diagnostics and health checks.

    Checks Python version, installed packages, API key config,
    and live network connectivity to all upstream services.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    run_doctor()


@app.command("tools")
def tools() -> None:
    """List all installed and registered ait tools.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    from ait_cli.discovery import list_registered_tools

    registered = list_registered_tools()
    if not registered:
        console.print("[yellow]No tools registered under the ait.tools entry-point group.[/yellow]")
        console.print("[dim]Install tool packages (e.g. uv sync) and re-run.[/dim]")
        return

    console.print("\n[bold]Installed ait tools:[/bold]")
    for name in registered:
        console.print(f"  [cyan]•[/cyan] {name}")
    console.print(
        f"\n[dim]{len(registered)} tool(s) registered. "
        "Run [bold]ait <tool> --help[/bold] for usage.[/dim]\n"
    )


# ── version callback ───────────────────────────────────────────────────────────


def _version_callback(value: bool) -> None:
    if value:
        try:
            ver = pkg_version("ait-cli")
        except Exception:  # noqa: BLE001
            ver = "unknown"
        console.print(f"ait version {ver}")
        raise typer.Exit()


@app.callback()
def main(
    version: Annotated[
        Optional[bool],
        typer.Option(
            "--version",
            "-V",
            help="Show version and exit.",
            callback=_version_callback,
            is_eager=True,
        ),
    ] = None,
) -> None:
    """AI Toolset unified CLI.

    Args:
        version: If true, print version and exit.

    Returns:
        None.

    Raises:
        typer.Exit: When ``--version`` is passed.
    """


# ── dynamic tool sub-app mounting ─────────────────────────────────────────────

def _mount_tool_apps() -> None:
    """Discover and mount all installed tool CLIs as sub-commands.

    Iterates ``importlib.metadata`` entry points in the ``ait.tools`` group
    and adds each Typer app to the root ``app``.  Broken or missing plugins
    are silently skipped; ``ait doctor`` will flag them.

    Args:
        None.

    Returns:
        None.

    Raises:
        None.
    """

    for name, tool_app in discover_tool_apps():
        app.add_typer(tool_app, name=name)


_mount_tool_apps()
