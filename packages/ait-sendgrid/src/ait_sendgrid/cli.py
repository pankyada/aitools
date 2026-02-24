"""Typer CLI for `ait-sendgrid`."""

from __future__ import annotations

import asyncio
import getpass
import os
from pathlib import Path

import typer
from ait_core.auth.api_key_store import APIKeyStore
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

from ait_sendgrid.commands.send import resolve_content, run_account, run_send, run_unsubscribes

app = typer.Typer(help="SendGrid API command-line interface")
auth_app = typer.Typer(help="Auth and API-key operations")
app.add_typer(auth_app, name="auth")


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


@auth_app.command("set-key")
def auth_set_key(
    env: bool = typer.Option(False, "--env", help="Read key from AIT_SENDGRID_API_KEY"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Set SendGrid API key in encrypted store.

    Examples:
        ait-sendgrid auth set-key
        ait-sendgrid auth set-key --env
    """

    start = command_timer()
    try:
        key_store = APIKeyStore()
        key = (
            os.getenv("AIT_SENDGRID_API_KEY", "").strip()
            if env
            else getpass.getpass("SendGrid API key: ").strip()
        )
        if not key:
            raise ToolsetError(
                code=ErrorCode.INVALID_INPUT,
                message="SendGrid API key cannot be empty",
                exit_code=ExitCode.INVALID_INPUT,
            )

        key_store.set_key("sendgrid", key)
        response = make_success_response(
            "ait-sendgrid", "auth set-key", {"configured": True}, start
        )
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-sendgrid", "auth set-key", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@auth_app.command("status")
def auth_status(output: OutputMode = typer.Option("json", "--output", "-o")) -> None:
    """Show SendGrid auth status.

    Examples:
        ait-sendgrid auth status
    """

    start = command_timer()
    try:
        key_store = APIKeyStore()
        key = key_store.get_key("sendgrid")
        response = make_success_response(
            "ait-sendgrid",
            "auth status",
            {
                "configured": key is not None,
                "preview": APIKeyStore.mask_value(key) if key else None,
            },
            start,
        )
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-sendgrid", "auth status", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@app.command("send")
def send(
    to: list[str] = typer.Option(..., "--to", help="Recipient email. Repeat for multiple."),
    subject: str = typer.Option(..., "--subject", help="Email subject"),
    from_email: str | None = typer.Option(None, "--from", help="Sender email"),
    text: str | None = typer.Option(None, "--text", help="Plain-text body"),
    text_file: Path | None = typer.Option(None, "--text-file", help="Plain-text body file"),
    html: str | None = typer.Option(None, "--html", help="HTML body"),
    html_file: Path | None = typer.Option(None, "--html-file", help="HTML body file"),
    cc: list[str] = typer.Option([], "--cc", help="CC recipient. Repeat for multiple."),
    bcc: list[str] = typer.Option([], "--bcc", help="BCC recipient. Repeat for multiple."),
    reply_to: str | None = typer.Option(None, "--reply-to", help="Reply-to address"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Send an email through SendGrid.

    Examples:
        ait-sendgrid send --to a@example.com --subject "Hi" --text "Hello" --from me@domain.com
    """

    start = command_timer()
    try:
        settings = load_settings()
        sender = from_email or settings.sendgrid.default_from
        if not sender:
            raise ToolsetError(
                code=ErrorCode.INVALID_INPUT,
                message="Provide --from or set sendgrid.default_from in config.toml",
                exit_code=ExitCode.INVALID_INPUT,
            )

        resolved_text, resolved_html = resolve_content(text, text_file, html, html_file)
        payload = asyncio.run(
            run_send(
                settings=settings,
                to=to,
                subject=subject,
                from_email=sender,
                text=resolved_text,
                html=resolved_html,
                cc=cc,
                bcc=bcc,
                reply_to=reply_to,
            )
        )
        response = make_success_response("ait-sendgrid", "send", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-sendgrid", "send", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@app.command("account")
def account(output: OutputMode = typer.Option("json", "--output", "-o")) -> None:
    """Get authenticated account details.

    Examples:
        ait-sendgrid account
    """

    start = command_timer()
    try:
        payload = asyncio.run(run_account(load_settings()))
        response = make_success_response("ait-sendgrid", "account", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-sendgrid", "account", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@app.command("unsubscribes")
def unsubscribes(
    limit: int = typer.Option(20, "--limit", help="Max records"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """List unsubscribed recipients.

    Examples:
        ait-sendgrid unsubscribes --limit 20
    """

    start = command_timer()
    try:
        payload = asyncio.run(run_unsubscribes(load_settings(), limit=limit))
        response = make_success_response("ait-sendgrid", "unsubscribes", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-sendgrid", "unsubscribes", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


if __name__ == "__main__":
    app()
