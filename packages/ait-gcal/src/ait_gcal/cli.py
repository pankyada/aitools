"""Typer CLI for `ait-gcal`."""

from __future__ import annotations

import asyncio

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

from ait_gcal.commands.calendars import run_list_calendars
from ait_gcal.commands.events import (
    run_create_event,
    run_delete_event,
    run_get_event,
    run_list_events,
)
from ait_gcal.scopes import SCOPES_FULL, SCOPES_READ

app = typer.Typer(help="Google Calendar command-line interface")
auth_app = typer.Typer(help="Google auth commands")
calendars_app = typer.Typer(help="Calendar list commands")
events_app = typer.Typer(help="Event commands")

app.add_typer(auth_app, name="auth")
app.add_typer(calendars_app, name="calendars")
app.add_typer(events_app, name="events")


def _print(mode: OutputMode, response: CommandResponse) -> None:
    """Render and print response envelope.

    Args:
        mode: Output mode.
        response: Response object.

    Returns:
        None.

    Raises:
        None.
    """

    rendered = format_output(response, mode)
    if rendered:
        print(rendered)


@auth_app.command("login")
def auth_login(
    full: bool = typer.Option(False, "--full", help="Request event-write scopes"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Login to Google Calendar via device-code flow.

    Examples:
        ait-gcal auth login
        ait-gcal auth login --full
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
            "ait-gcal",
            "auth login",
            {"authorized": True, "scopes": scopes},
            start,
        )
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gcal", "auth login", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@auth_app.command("logout")
def auth_logout(
    full: bool = typer.Option(False, "--full", help="Logout full scope bundle"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Remove saved Calendar OAuth token bundle.

    Examples:
        ait-gcal auth logout
    """

    start = command_timer()
    try:
        settings = load_settings()
        auth = GoogleAuthClient(settings=settings)
        scopes = SCOPES_FULL if full else SCOPES_READ
        removed = auth.logout(scopes)
        response = make_success_response(
            "ait-gcal",
            "auth logout",
            {"removed": removed, "scopes": scopes},
            start,
        )
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gcal", "auth logout", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@auth_app.command("status")
def auth_status(output: OutputMode = typer.Option("json", "--output", "-o")) -> None:
    """Show whether Calendar tokens exist for read/full scopes.

    Examples:
        ait-gcal auth status
    """

    start = command_timer()
    try:
        settings = load_settings()
        auth = GoogleAuthClient(settings=settings)
        store = TokenStore()
        response = make_success_response(
            "ait-gcal",
            "auth status",
            {
                "read_scopes": store.load_token_bundle(auth._scope_key(SCOPES_READ)) is not None,
                "full_scopes": store.load_token_bundle(auth._scope_key(SCOPES_FULL)) is not None,
            },
            start,
        )
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gcal", "auth status", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@calendars_app.command("list")
def calendars_list(
    max_results: int = typer.Option(100, "--max", help="Maximum calendars"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """List user calendars.

    Examples:
        ait-gcal calendars list --max 100
    """

    start = command_timer()
    try:
        payload = asyncio.run(run_list_calendars(load_settings(), max_results=max_results))
        response = make_success_response("ait-gcal", "calendars list", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gcal", "calendars list", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@events_app.command("list")
def events_list(
    calendar_id: str = typer.Option("primary", "--calendar", help="Calendar id"),
    max_results: int = typer.Option(20, "--max", help="Maximum events"),
    time_min: str | None = typer.Option(None, "--from", help="Lower datetime bound (RFC3339)"),
    time_max: str | None = typer.Option(None, "--to", help="Upper datetime bound (RFC3339)"),
    query: str | None = typer.Option(None, "--query", "-q", help="Text search query"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """List calendar events.

    Examples:
        ait-gcal events list --calendar primary --max 20
        ait-gcal events list --from "2026-03-01T00:00:00Z" --to "2026-03-31T23:59:59Z"
    """

    start = command_timer()
    try:
        payload = asyncio.run(
            run_list_events(
                settings=load_settings(),
                calendar_id=calendar_id,
                max_results=max_results,
                time_min=time_min,
                time_max=time_max,
                query=query,
            )
        )
        response = make_success_response("ait-gcal", "events list", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gcal", "events list", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@events_app.command("get")
def events_get(
    event_id: str = typer.Argument(..., help="Event id"),
    calendar_id: str = typer.Option("primary", "--calendar", help="Calendar id"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Get event details by id.

    Examples:
        ait-gcal events get <event_id> --calendar primary
    """

    start = command_timer()
    try:
        payload = asyncio.run(
            run_get_event(settings=load_settings(), calendar_id=calendar_id, event_id=event_id)
        )
        response = make_success_response("ait-gcal", "events get", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gcal", "events get", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@events_app.command("create")
def events_create(
    summary: str = typer.Option(..., "--summary", help="Event summary/title"),
    start_at: str = typer.Option(..., "--start", help="Start datetime RFC3339"),
    end_at: str = typer.Option(..., "--end", help="End datetime RFC3339"),
    calendar_id: str = typer.Option("primary", "--calendar", help="Calendar id"),
    description: str | None = typer.Option(None, "--description", help="Description"),
    location: str | None = typer.Option(None, "--location", help="Location"),
    timezone: str | None = typer.Option(None, "--timezone", help="Timezone (e.g. Asia/Kolkata)"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Create a calendar event.

    Examples:
        ait-gcal events create --summary "Standup" --start "2026-03-01T09:00:00Z" --end "2026-03-01T09:15:00Z"
    """

    start = command_timer()
    try:
        payload = asyncio.run(
            run_create_event(
                settings=load_settings(),
                calendar_id=calendar_id,
                summary=summary,
                start=start_at,
                end=end_at,
                description=description,
                location=location,
                timezone=timezone,
            )
        )
        response = make_success_response("ait-gcal", "events create", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gcal", "events create", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@events_app.command("delete")
def events_delete(
    event_id: str = typer.Argument(..., help="Event id"),
    calendar_id: str = typer.Option("primary", "--calendar", help="Calendar id"),
    confirm: bool = typer.Option(False, "--confirm", help="Required for delete"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Delete an event.

    Examples:
        ait-gcal events delete <event_id> --calendar primary --confirm
    """

    start = command_timer()
    try:
        if not confirm:
            raise ToolsetError(
                code=ErrorCode.CONFIRMATION_REQUIRED,
                message="Deleting an event requires --confirm",
                exit_code=ExitCode.INVALID_INPUT,
                details={"confirmation_token": "DELETE_EVENT"},
            )

        payload = asyncio.run(
            run_delete_event(settings=load_settings(), calendar_id=calendar_id, event_id=event_id)
        )
        response = make_success_response("ait-gcal", "events delete", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gcal", "events delete", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


if __name__ == "__main__":
    app()
