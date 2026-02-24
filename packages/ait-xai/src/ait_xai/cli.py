"""Typer CLI for `ait-xai`."""

from __future__ import annotations

import asyncio
import getpass
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

from ait_xai.commands.chat import resolve_prompt, run_chat, run_chat_interactive
from ait_xai.commands.imagegen import run_image
from ait_xai.commands.videogen import run_video

app = typer.Typer(help="xAI API command-line interface")
auth_app = typer.Typer(help="Auth and API-key operations")
app.add_typer(auth_app, name="auth")


def _print_response(mode: OutputMode, response: CommandResponse) -> None:
    """Print response object to stdout.

    Args:
        mode: Output mode.
        response: Command response object.

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
    env: bool = typer.Option(False, "--env", help="Read key from AIT_XAI_API_KEY env var"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Set xAI API key in encrypted local store.

    Examples:
        ait-xai auth set-key
        ait-xai auth set-key --env
    """

    start = command_timer()
    try:
        key_store = APIKeyStore()
        if env:
            import os

            key = os.getenv("AIT_XAI_API_KEY", "")
            if not key:
                raise ToolsetError(
                    code=ErrorCode.INVALID_INPUT,
                    message="AIT_XAI_API_KEY is empty or not set",
                    exit_code=ExitCode.INVALID_INPUT,
                )
        else:
            key = getpass.getpass("xAI API key: ").strip()
            if not key:
                raise ToolsetError(
                    code=ErrorCode.INVALID_INPUT,
                    message="API key cannot be empty",
                    exit_code=ExitCode.INVALID_INPUT,
                )

        key_store.set_key("xai", key)
        response = make_success_response("ait-xai", "auth set-key", {"configured": True}, start)
        _print_response(output, response)
    except Exception as exc:
        response = make_error_response("ait-xai", "auth set-key", start, exc)
        _print_response(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@auth_app.command("status")
def auth_status(output: OutputMode = typer.Option("json", "--output", "-o")) -> None:
    """Show xAI auth status.

    Examples:
        ait-xai auth status
    """

    start = command_timer()
    try:
        key_store = APIKeyStore()
        key = key_store.get_key("xai")
        response = make_success_response(
            "ait-xai",
            "auth status",
            {
                "configured": key is not None,
                "preview": APIKeyStore.mask_value(key) if key else None,
            },
            start,
        )
        _print_response(output, response)
    except Exception as exc:
        response = make_error_response("ait-xai", "auth status", start, exc)
        _print_response(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@app.command("chat")
def chat(
    prompt: str | None = typer.Option(None, "--prompt", help="Direct prompt text"),
    prompt_file: Path | None = typer.Option(None, "--prompt-file", help="Read prompt from file"),
    stdin: bool = typer.Option(False, "--stdin", help="Read prompt from stdin"),
    system: str | None = typer.Option(None, "--system", help="System prompt"),
    model: str | None = typer.Option(None, "--model", help="Model override"),
    temperature: float = typer.Option(0.7, "--temperature", help="Sampling temperature"),
    max_tokens: int | None = typer.Option(None, "--max-tokens", help="Max response tokens"),
    stream: bool = typer.Option(False, "--stream/--no-stream", help="Stream response"),
    interactive: bool = typer.Option(False, "--interactive", help="Interactive chat mode"),
    json_mode: bool = typer.Option(False, "--json-mode", help="Request JSON output from model"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Create a chat completion.

    Examples:
        ait-xai chat --prompt "Summarize this text"
        ait-xai chat --stdin --system "Extract tasks"
        ait-xai chat --interactive
    """

    start = command_timer()
    try:
        settings = load_settings()
        if interactive:
            payload = asyncio.run(
                run_chat_interactive(
                    settings=settings,
                    system=system,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
            )
        else:
            resolved_prompt = resolve_prompt(
                prompt=prompt, prompt_file=prompt_file, use_stdin=stdin
            )
            payload = asyncio.run(
                run_chat(
                    settings=settings,
                    prompt=resolved_prompt,
                    system=system,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    stream=stream,
                    json_mode=json_mode,
                )
            )
        response = make_success_response("ait-xai", "chat", payload, start)
        _print_response(output, response)
    except Exception as exc:
        response = make_error_response("ait-xai", "chat", start, exc)
        _print_response(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@app.command("image")
def image(
    prompt: str = typer.Argument(..., help="Prompt text"),
    output_path: Path | None = typer.Option(None, "--output", help="Write image to file"),
    size: str = typer.Option("1024x1024", "--size", help="Image size"),
    model: str | None = typer.Option(None, "--model", help="Model override"),
    num: int = typer.Option(1, "--num", help="Number of images"),
    out_format: OutputMode = typer.Option("json", "--format", "-o", help="Output format"),
) -> None:
    """Generate image(s) from prompt.

    Examples:
        ait-xai image "A steel robot in rain"
        ait-xai image "Cat" --num 2 --output ./cat.png
    """

    start = command_timer()
    try:
        settings = load_settings()
        payload = asyncio.run(
            run_image(
                settings=settings,
                prompt=prompt,
                output=output_path,
                size=size,
                model=model,
                num=num,
            )
        )
        response = make_success_response("ait-xai", "image", payload, start)
        _print_response(out_format, response)
    except Exception as exc:
        response = make_error_response("ait-xai", "image", start, exc)
        _print_response(out_format, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@app.command("video")
def video(
    prompt: str = typer.Argument(..., help="Prompt text"),
    duration: int | None = typer.Option(None, "--duration", help="Requested duration in seconds"),
    model: str | None = typer.Option(None, "--model", help="Model override"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Generate a video request from prompt.

    Examples:
        ait-xai video "A drone shot over mountains" --duration 8
    """

    start = command_timer()
    try:
        settings = load_settings()
        payload = asyncio.run(
            run_video(settings=settings, prompt=prompt, duration=duration, model=model)
        )
        response = make_success_response("ait-xai", "video", payload, start)
        _print_response(output, response)
    except Exception as exc:
        response = make_error_response("ait-xai", "video", start, exc)
        _print_response(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


if __name__ == "__main__":
    app()
