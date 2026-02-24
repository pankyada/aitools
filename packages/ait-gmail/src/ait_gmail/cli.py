"""Typer CLI for `ait-gmail`."""

from __future__ import annotations

import asyncio
from datetime import date, datetime
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

from ait_gmail.commands.analyze import run_senders, run_stats, run_summary, run_threads
from ait_gmail.commands.delete import run_bulk, run_permanent, run_trash
from ait_gmail.commands.read import run_get, run_list, run_search, run_thread
from ait_gmail.commands.send import run_compose, run_forward, run_reply
from ait_gmail.scopes import SCOPES_FULL, SCOPES_READ

app = typer.Typer(help="Gmail command-line interface")
auth_app = typer.Typer(help="Google auth commands")
read_app = typer.Typer(help="Read/search commands")
send_app = typer.Typer(help="Send/reply/forward commands")
delete_app = typer.Typer(help="Delete and trash commands")
analyze_app = typer.Typer(help="Mailbox analysis commands")

app.add_typer(auth_app, name="auth")
app.add_typer(read_app, name="read")
app.add_typer(send_app, name="send")
app.add_typer(delete_app, name="delete")
app.add_typer(analyze_app, name="analyze")


def _print(mode: OutputMode, response: CommandResponse) -> None:
    """Render and print command response.

    Args:
        mode: Selected output mode.
        response: Response envelope.

    Returns:
        None.

    Raises:
        None.
    """

    rendered = format_output(response, mode)
    if rendered:
        print(rendered)


def _parse_date(value: str | None) -> date | None:
    """Parse YYYY-MM-DD string to date.

    Args:
        value: Input string.

    Returns:
        Parsed date or None.

    Raises:
        ValueError: If format is invalid.
    """

    if value is None:
        return None
    return datetime.strptime(value, "%Y-%m-%d").date()


@auth_app.command("login")
def auth_login(
    full: bool = typer.Option(False, "--full", help="Request full read/send/modify scopes"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Login to Google via device-code flow.

    Examples:
        ait-gmail auth login
        ait-gmail auth login --full
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
            "ait-gmail",
            "auth login",
            {"authorized": True, "scopes": scopes},
            start,
        )
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gmail", "auth login", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@auth_app.command("logout")
def auth_logout(
    full: bool = typer.Option(False, "--full", help="Logout full scopes instead of read-only"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Remove saved Gmail OAuth token bundle.

    Examples:
        ait-gmail auth logout
        ait-gmail auth logout --full
    """

    start = command_timer()
    try:
        settings = load_settings()
        auth = GoogleAuthClient(settings=settings)
        scopes = SCOPES_FULL if full else SCOPES_READ
        removed = auth.logout(scopes)
        response = make_success_response(
            "ait-gmail",
            "auth logout",
            {"removed": removed, "scopes": scopes},
            start,
        )
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gmail", "auth logout", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@auth_app.command("status")
def auth_status(output: OutputMode = typer.Option("json", "--output", "-o")) -> None:
    """Show whether Gmail tokens exist for read/full scope sets.

    Examples:
        ait-gmail auth status
    """

    start = command_timer()
    try:
        store = TokenStore()
        read_key = GoogleAuthClient(settings=load_settings())._scope_key(SCOPES_READ)
        full_key = GoogleAuthClient(settings=load_settings())._scope_key(SCOPES_FULL)
        response = make_success_response(
            "ait-gmail",
            "auth status",
            {
                "read_scopes": store.load_token_bundle(read_key) is not None,
                "full_scopes": store.load_token_bundle(full_key) is not None,
            },
            start,
        )
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gmail", "auth status", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@read_app.command("list")
def read_list(
    label: str = typer.Option("INBOX", "--label", help="Label filter"),
    max_results: int = typer.Option(20, "--max", help="Max messages"),
    unread: bool = typer.Option(False, "--unread", help="Unread-only"),
    after: str | None = typer.Option(None, "--after", help="After date (YYYY-MM-DD)"),
    before: str | None = typer.Option(None, "--before", help="Before date (YYYY-MM-DD)"),
    from_filter: str | None = typer.Option(None, "--from", help="Sender filter"),
    has_attachment: bool = typer.Option(False, "--has-attachment", help="Attachment-only"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """List Gmail messages.

    Examples:
        ait-gmail read list --unread --max 20
        ait-gmail read list --label SENT --after 2026-02-01
    """

    start = command_timer()
    try:
        settings = load_settings()
        payload = asyncio.run(
            run_list(
                settings=settings,
                label=label,
                max_results=max_results,
                unread=unread,
                after=_parse_date(after),
                before=_parse_date(before),
                from_filter=from_filter,
                has_attachment=has_attachment,
            )
        )
        response = make_success_response("ait-gmail", "read list", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gmail", "read list", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@read_app.command("get")
def read_get(
    message_id: str = typer.Argument(..., help="Message ID"),
    fmt: str = typer.Option("full", "--format", help="Fetch format: full|metadata|minimal"),
    save_attachments: Path | None = typer.Option(None, "--save-attachments", help="Attachment dir"),
    body_only: bool = typer.Option(False, "--body-only", help="Only return body text"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Get a Gmail message by ID.

    Examples:
        ait-gmail read get 18f91afc...
        ait-gmail read get 18f91afc... --body-only
    """

    _ = save_attachments
    start = command_timer()
    try:
        settings = load_settings()
        payload = asyncio.run(
            run_get(settings=settings, message_id=message_id, fmt=fmt, body_only=body_only)
        )
        response = make_success_response("ait-gmail", "read get", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gmail", "read get", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@read_app.command("search")
def read_search(
    query: str = typer.Argument(..., help="Gmail query"),
    max_results: int = typer.Option(20, "--max", help="Max messages"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Search Gmail messages.

    Examples:
        ait-gmail read search "from:alice newer_than:7d"
    """

    start = command_timer()
    try:
        settings = load_settings()
        payload = asyncio.run(run_search(settings=settings, query=query, max_results=max_results))
        response = make_success_response("ait-gmail", "read search", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gmail", "read search", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@read_app.command("thread")
def read_thread(
    thread_id: str = typer.Argument(..., help="Thread ID"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Get an email thread by ID.

    Examples:
        ait-gmail read thread 18f91afc...
    """

    start = command_timer()
    try:
        settings = load_settings()
        payload = asyncio.run(run_thread(settings=settings, thread_id=thread_id))
        response = make_success_response("ait-gmail", "read thread", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gmail", "read thread", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@send_app.command("compose")
def send_compose(
    to: str = typer.Option(..., "--to", help="Recipient address"),
    subject: str = typer.Option(..., "--subject", help="Email subject"),
    body: str | None = typer.Option(None, "--body", help="Body text"),
    body_file: Path | None = typer.Option(None, "--body-file", help="Body file path"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Compose and send an email.

    Examples:
        ait-gmail send compose --to a@example.com --subject Hi --body "Hello"
        ait-gmail send compose --to a@example.com --subject Hi --body-file ./body.txt
    """

    start = command_timer()
    try:
        resolved_body = body or (body_file.read_text(encoding="utf-8") if body_file else "")
        if not resolved_body:
            raise ToolsetError(
                code=ErrorCode.INVALID_INPUT,
                message="Provide --body or --body-file",
                exit_code=ExitCode.INVALID_INPUT,
            )
        settings = load_settings()
        payload = asyncio.run(
            run_compose(settings=settings, to=to, subject=subject, body=resolved_body)
        )
        response = make_success_response("ait-gmail", "send compose", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gmail", "send compose", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@send_app.command("reply")
def send_reply(
    message_id: str = typer.Argument(..., help="Source message ID"),
    body: str = typer.Option(..., "--body", help="Reply body"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Reply to a message.

    Examples:
        ait-gmail send reply <message_id> --body "Thanks"
    """

    start = command_timer()
    try:
        settings = load_settings()
        payload = asyncio.run(run_reply(settings=settings, message_id=message_id, body=body))
        response = make_success_response("ait-gmail", "send reply", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gmail", "send reply", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@send_app.command("forward")
def send_forward(
    message_id: str = typer.Argument(..., help="Source message ID"),
    to: str = typer.Option(..., "--to", help="Recipient"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Forward a message.

    Examples:
        ait-gmail send forward <message_id> --to b@example.com
    """

    start = command_timer()
    try:
        settings = load_settings()
        payload = asyncio.run(run_forward(settings=settings, message_id=message_id, to=to))
        response = make_success_response("ait-gmail", "send forward", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gmail", "send forward", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@delete_app.command("trash")
def delete_trash(
    message_ids: list[str] = typer.Argument(..., help="Message IDs"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Trash one or more messages.

    Examples:
        ait-gmail delete trash <message_id_1> <message_id_2>
    """

    start = command_timer()
    try:
        settings = load_settings()
        payload = asyncio.run(run_trash(settings=settings, message_ids=message_ids))
        response = make_success_response("ait-gmail", "delete trash", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gmail", "delete trash", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@delete_app.command("permanent")
def delete_permanent(
    message_ids: list[str] = typer.Argument(..., help="Message IDs"),
    confirm: bool = typer.Option(False, "--confirm", help="Required for permanent delete"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Permanently delete one or more messages.

    Examples:
        ait-gmail delete permanent <message_id> --confirm
    """

    start = command_timer()
    try:
        if not confirm:
            raise ToolsetError(
                code=ErrorCode.CONFIRMATION_REQUIRED,
                message="Permanent delete requires --confirm",
                exit_code=ExitCode.INVALID_INPUT,
                details={"confirmation_token": "PERMANENT_DELETE"},
            )

        settings = load_settings()
        payload = asyncio.run(run_permanent(settings=settings, message_ids=message_ids))
        response = make_success_response("ait-gmail", "delete permanent", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gmail", "delete permanent", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@delete_app.command("bulk")
def delete_bulk(
    query: str = typer.Option(..., "--query", help="Query for bulk delete"),
    older_than: int = typer.Option(..., "--older-than", help="Age threshold in days"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show matches only"),
    confirm: bool = typer.Option(False, "--confirm", help="Required unless --dry-run"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Bulk delete messages matching query and age.

    Examples:
        ait-gmail delete bulk --query "category:promotions" --older-than 30 --dry-run
        ait-gmail delete bulk --query "category:promotions" --older-than 30 --confirm
    """

    start = command_timer()
    try:
        if not dry_run and not confirm:
            raise ToolsetError(
                code=ErrorCode.CONFIRMATION_REQUIRED,
                message="Bulk delete requires --confirm unless --dry-run is set",
                exit_code=ExitCode.INVALID_INPUT,
                details={"confirmation_token": "BULK_DELETE"},
            )

        settings = load_settings()
        payload = asyncio.run(
            run_bulk(settings=settings, query=query, older_than=older_than, dry_run=dry_run)
        )
        response = make_success_response("ait-gmail", "delete bulk", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gmail", "delete bulk", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@analyze_app.command("summary")
def analyze_summary(
    days: int = typer.Option(7, "--days", help="Window days"),
    label: str = typer.Option("INBOX", "--label", help="Label filter"),
    use_llm: bool = typer.Option(
        True, "--use-llm/--no-llm", help="Enable LLM summary when available"
    ),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Summarize inbox activity.

    Examples:
        ait-gmail analyze summary --days 7
        ait-gmail analyze summary --no-llm
    """

    start = command_timer()
    try:
        settings = load_settings()
        payload = asyncio.run(
            run_summary(settings=settings, days=days, label=label, use_llm=use_llm)
        )
        response = make_success_response("ait-gmail", "analyze summary", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gmail", "analyze summary", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@analyze_app.command("stats")
def analyze_stats(
    days: int = typer.Option(30, "--days", help="Window days"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Show inbox stats.

    Examples:
        ait-gmail analyze stats --days 30
    """

    start = command_timer()
    try:
        settings = load_settings()
        payload = asyncio.run(run_stats(settings=settings, days=days))
        response = make_success_response("ait-gmail", "analyze stats", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gmail", "analyze stats", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@analyze_app.command("senders")
def analyze_senders(
    top: int = typer.Option(20, "--top", help="Top sender count"),
    days: int = typer.Option(30, "--days", help="Window days"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """List top senders.

    Examples:
        ait-gmail analyze senders --top 20 --days 30
    """

    start = command_timer()
    try:
        settings = load_settings()
        payload = asyncio.run(run_senders(settings=settings, top=top, days=days))
        response = make_success_response("ait-gmail", "analyze senders", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gmail", "analyze senders", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@analyze_app.command("threads")
def analyze_threads(
    unresolved: bool = typer.Option(False, "--unresolved", help="Only unresolved-like threads"),
    days: int = typer.Option(7, "--days", help="Window days"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Analyze thread activity.

    Examples:
        ait-gmail analyze threads --unresolved --days 7
    """

    start = command_timer()
    try:
        settings = load_settings()
        payload = asyncio.run(run_threads(settings=settings, unresolved=unresolved, days=days))
        response = make_success_response("ait-gmail", "analyze threads", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-gmail", "analyze threads", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


if __name__ == "__main__":
    app()
