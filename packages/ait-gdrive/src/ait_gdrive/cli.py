"""Typer CLI for `ait-gdrive`."""

from __future__ import annotations

import asyncio
from pathlib import Path

import typer
from ait_core.auth.google_auth import GoogleAuthClient
from ait_core.auth.token_store import TokenStore
from ait_core.config.settings import load_settings
from ait_core.errors import ErrorCode, ExitCode, ToolsetError
from ait_core.output.formatter import (
    CommandResponse,
    OutputMode,
    command_timer,
    format_output,
    make_error_response,
    make_success_response,
)
from rich.console import Console
from rich.panel import Panel

from ait_gdrive.commands.analyze import run_duplicates, run_large, run_shared, run_storage
from ait_gdrive.commands.create import run_create_file, run_create_folder
from ait_gdrive.commands.delete import run_delete
from ait_gdrive.commands.list import run_list
from ait_gdrive.commands.read import run_read
from ait_gdrive.commands.search import run_search
from ait_gdrive.commands.update import run_update
from ait_gdrive.scopes import SCOPES_FULL, SCOPES_READ

app = typer.Typer(help="Google Drive command-line interface")
auth_app = typer.Typer(help="Google auth commands")
create_app = typer.Typer(help="Create/upload commands")
analyze_app = typer.Typer(help="Drive analysis commands")

app.add_typer(auth_app, name="auth")
app.add_typer(create_app, name="create")
app.add_typer(analyze_app, name="analyze")


def _print(mode: OutputMode, response: CommandResponse) -> None:
    """Render and print response.

    Args:
        mode: Output mode.
        response: Response envelope.

    Returns:
        None.

    Raises:
        None.
    """

    rendered = format_output(response, mode)
    if rendered:
        print(rendered)


def _parse_size(value: str) -> int:
    """Parse human-readable size string to bytes.

    Args:
        value: Size input like `10MB`.

    Returns:
        Integer bytes.

    Raises:
        ValueError: If size format is invalid.
    """

    text = value.strip().upper()
    multipliers = [
        ("GB", 1024**3),
        ("MB", 1024**2),
        ("KB", 1024),
        ("B", 1),
    ]
    for unit, factor in multipliers:
        if text.endswith(unit):
            number = float(text[: -len(unit)].strip())
            return int(number * factor)
    return int(text)


@auth_app.command("login")
def auth_login(
    full: bool = typer.Option(False, "--full", help="Request full drive scope"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Login to Google with device code flow.

    Examples:
        ait-gdrive auth login
        ait-gdrive auth login --full
    """

    start = command_timer()
    try:
        settings = load_settings()
        auth = GoogleAuthClient(settings=settings)
        scopes = SCOPES_FULL if full else SCOPES_READ
        device = asyncio.run(auth.request_device_code(scopes))

        console = Console()
        console.print(
            Panel(
                f"Go to: {device.verification_url}\nEnter code: {device.user_code}",
                title="Google Device Login",
            )
        )
        token = asyncio.run(
            auth.poll_for_tokens(device.device_code, device.interval, device.expires_in)
        )
        auth.store_token_response(scopes=scopes, token=token)

        response = make_success_response(
            "ait-gdrive", "auth login", {"authorized": True, "scopes": scopes}, start
        )
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gdrive", "auth login", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@auth_app.command("logout")
def auth_logout(
    full: bool = typer.Option(False, "--full", help="Logout full scope bundle"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Remove Drive auth token bundle.

    Examples:
        ait-gdrive auth logout
    """

    start = command_timer()
    try:
        settings = load_settings()
        auth = GoogleAuthClient(settings=settings)
        scopes = SCOPES_FULL if full else SCOPES_READ
        removed = auth.logout(scopes)
        response = make_success_response("ait-gdrive", "auth logout", {"removed": removed}, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gdrive", "auth logout", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@auth_app.command("status")
def auth_status(output: OutputMode = typer.Option("json", "--output", "-o")) -> None:
    """Show saved auth bundle status.

    Examples:
        ait-gdrive auth status
    """

    start = command_timer()
    try:
        settings = load_settings()
        auth = GoogleAuthClient(settings=settings)
        store = TokenStore()
        response = make_success_response(
            "ait-gdrive",
            "auth status",
            {
                "read_scopes": store.load_token_bundle(auth._scope_key(SCOPES_READ)) is not None,
                "full_scopes": store.load_token_bundle(auth._scope_key(SCOPES_FULL)) is not None,
            },
            start,
        )
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gdrive", "auth status", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@app.command("list")
def list_files(
    path_value: str | None = typer.Argument(None, help="Folder path or ID"),
    max_results: int = typer.Option(100, "--max", help="Maximum files"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """List files.

    Examples:
        ait-gdrive list
        ait-gdrive list Projects/2026 --max 200
    """

    start = command_timer()
    try:
        payload = asyncio.run(
            run_list(load_settings(), path_value=path_value, max_results=max_results)
        )
        response = make_success_response("ait-gdrive", "list", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gdrive", "list", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@app.command("read")
def read_file(
    file_id_or_path: str = typer.Argument(..., help="File ID or path"),
    save_to: Path | None = typer.Option(None, "--save-to", help="Destination path"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Download or export a file.

    Examples:
        ait-gdrive read 1AbCDef...
        ait-gdrive read Projects/2026/report.docx --save-to /tmp/report.docx
    """

    start = command_timer()
    try:
        payload = asyncio.run(
            run_read(load_settings(), file_id_or_path=file_id_or_path, save_to=save_to)
        )
        response = make_success_response("ait-gdrive", "read", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gdrive", "read", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@create_app.command("file")
def create_file(
    local_path: Path = typer.Argument(..., help="Local file to upload"),
    parent: str | None = typer.Option(None, "--parent", help="Parent folder path/ID"),
    name: str | None = typer.Option(None, "--name", help="Remote name override"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Upload a local file.

    Examples:
        ait-gdrive create file ./notes.txt --parent Projects/2026
    """

    start = command_timer()
    try:
        payload = asyncio.run(
            run_create_file(load_settings(), local_path=local_path, parent=parent, name=name)
        )
        response = make_success_response("ait-gdrive", "create file", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gdrive", "create file", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@create_app.command("folder")
def create_folder(
    name: str = typer.Argument(..., help="Folder name"),
    parent: str | None = typer.Option(None, "--parent", help="Parent folder path/ID"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Create a folder.

    Examples:
        ait-gdrive create folder Reports --parent Projects/2026
    """

    start = command_timer()
    try:
        payload = asyncio.run(run_create_folder(load_settings(), name=name, parent=parent))
        response = make_success_response("ait-gdrive", "create folder", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gdrive", "create folder", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@app.command("update")
def update_file(
    file_id_or_path: str = typer.Argument(..., help="File ID or path"),
    file: Path | None = typer.Option(None, "--file", help="Replacement local file"),
    rename: str | None = typer.Option(None, "--rename", help="New name"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Update file contents and/or metadata.

    Examples:
        ait-gdrive update <id> --file ./updated.txt
        ait-gdrive update <id> --rename new-name.txt
    """

    start = command_timer()
    try:
        payload = asyncio.run(
            run_update(
                load_settings(), file_id_or_path=file_id_or_path, local_file=file, rename=rename
            )
        )
        response = make_success_response("ait-gdrive", "update", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gdrive", "update", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@app.command("delete")
def delete_files(
    targets: list[str] = typer.Argument(..., help="File IDs or paths"),
    permanent: bool = typer.Option(False, "--permanent", help="Permanently delete"),
    confirm: bool = typer.Option(False, "--confirm", help="Required for permanent delete"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Trash or delete files.

    Examples:
        ait-gdrive delete <id>
        ait-gdrive delete <id1> <id2> --permanent --confirm
    """

    start = command_timer()
    try:
        if permanent and not confirm:
            raise ToolsetError(
                code=ErrorCode.CONFIRMATION_REQUIRED,
                message="Permanent delete requires --confirm",
                exit_code=ExitCode.INVALID_INPUT,
                details={"confirmation_token": "PERMANENT_DELETE"},
            )
        payload = asyncio.run(run_delete(load_settings(), targets=targets, permanent=permanent))
        response = make_success_response("ait-gdrive", "delete", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gdrive", "delete", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@app.command("search")
def search_files(
    query: str = typer.Argument(..., help="Drive query syntax"),
    max_results: int = typer.Option(50, "--max", help="Maximum results"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Search Drive files.

    Examples:
        ait-gdrive search "fullText contains 'invoice'"
    """

    start = command_timer()
    try:
        payload = asyncio.run(run_search(load_settings(), query=query, max_results=max_results))
        response = make_success_response("ait-gdrive", "search", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gdrive", "search", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@analyze_app.command("storage")
def analyze_storage(output: OutputMode = typer.Option("json", "--output", "-o")) -> None:
    """Show storage summary.

    Examples:
        ait-gdrive analyze storage
    """

    start = command_timer()
    try:
        payload = asyncio.run(run_storage(load_settings()))
        response = make_success_response("ait-gdrive", "analyze storage", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gdrive", "analyze storage", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@analyze_app.command("duplicates")
def analyze_duplicates(
    folder: str | None = typer.Option(None, "--folder", help="Optional folder path/ID"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Find duplicate file names.

    Examples:
        ait-gdrive analyze duplicates
    """

    start = command_timer()
    try:
        payload = asyncio.run(run_duplicates(load_settings(), folder=folder))
        response = make_success_response("ait-gdrive", "analyze duplicates", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gdrive", "analyze duplicates", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@analyze_app.command("shared")
def analyze_shared(
    who: bool = typer.Option(False, "--who", help="Show owner breakdown"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Analyze shared ownership patterns.

    Examples:
        ait-gdrive analyze shared --who
    """

    start = command_timer()
    try:
        payload = asyncio.run(run_shared(load_settings(), who=who))
        response = make_success_response("ait-gdrive", "analyze shared", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gdrive", "analyze shared", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@analyze_app.command("large")
def analyze_large(
    top: int = typer.Option(20, "--top", help="Top largest files"),
    min_size: str = typer.Option("10MB", "--min-size", help="Minimum size threshold"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """List largest files above threshold.

    Examples:
        ait-gdrive analyze large --top 20 --min-size 10MB
    """

    start = command_timer()
    try:
        payload = asyncio.run(
            run_large(load_settings(), top=top, min_size_bytes=_parse_size(min_size))
        )
        response = make_success_response("ait-gdrive", "analyze large", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gdrive", "analyze large", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


if __name__ == "__main__":
    app()
