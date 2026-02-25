"""Typer CLI for `ait-social`."""

from __future__ import annotations

import asyncio
import getpass
import json
import os

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

from ait_social.commands import (
    SOCIAL_PLATFORMS,
    run_create_post,
    run_get_profile,
    service_name_for_platform,
)
from ait_social.models import SocialPlatform

app = typer.Typer(help="Social media command-line interface")
auth_app = typer.Typer(help="Auth token management")
post_app = typer.Typer(help="Post operations")
profile_app = typer.Typer(help="Profile operations")
platforms_app = typer.Typer(help="Platform information")

app.add_typer(auth_app, name="auth")
app.add_typer(post_app, name="post")
app.add_typer(profile_app, name="profile")
app.add_typer(platforms_app, name="platforms")


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


@platforms_app.command("list")
def platforms_list(output: OutputMode = typer.Option("json", "--output", "-o")) -> None:
    """List supported social platforms.

    Examples:
        ait-social platforms list
    """

    start = command_timer()
    try:
        response = make_success_response(
            "ait-social",
            "platforms list",
            {"platforms": list(SOCIAL_PLATFORMS)},
            start,
        )
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-social", "platforms list", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@auth_app.command("set-token")
def auth_set_token(
    platform: SocialPlatform = typer.Option(..., "--platform", help="Platform name"),
    env: bool = typer.Option(False, "--env", help="Read from AIT_SOCIAL_TOKEN env var"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Set a platform access token.

    Examples:
        ait-social auth set-token --platform twitter
        ait-social auth set-token --platform linkedin --env
    """

    start = command_timer()
    try:
        if env:
            token = os.getenv("AIT_SOCIAL_TOKEN", "").strip()
        else:
            token = getpass.getpass(f"{platform} token: ").strip()

        if not token:
            raise ToolsetError(
                code=ErrorCode.INVALID_INPUT,
                message="Token cannot be empty",
                exit_code=ExitCode.INVALID_INPUT,
            )

        key_store = APIKeyStore()
        service_name = service_name_for_platform(platform)
        key_store.set_key(service_name, token)

        response = make_success_response(
            "ait-social",
            "auth set-token",
            {
                "platform": platform,
                "configured": True,
            },
            start,
        )
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-social", "auth set-token", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@auth_app.command("status")
def auth_status(
    platform: SocialPlatform | None = typer.Option(None, "--platform", help="Optional platform"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Show configured token status.

    Examples:
        ait-social auth status
        ait-social auth status --platform instagram
    """

    start = command_timer()
    try:
        key_store = APIKeyStore()
        platforms = [platform] if platform else list(SOCIAL_PLATFORMS)
        status: dict[str, dict[str, object]] = {}
        for item in platforms:
            service_name = service_name_for_platform(item)
            token = key_store.get_key(service_name)
            status[item] = {
                "configured": token is not None,
                "preview": APIKeyStore.mask_value(token) if token else None,
            }

        response = make_success_response(
            "ait-social",
            "auth status",
            {"status": status},
            start,
        )
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-social", "auth status", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@post_app.command("create")
def post_create(
    platform: SocialPlatform = typer.Option(..., "--platform", help="Platform name"),
    text: str | None = typer.Option(None, "--text", help="Post text/caption"),
    title: str | None = typer.Option(None, "--title", help="Post title"),
    media_url: str | None = typer.Option(None, "--media-url", help="Media URL"),
    link_url: str | None = typer.Option(None, "--link-url", help="Link URL"),
    account_id: str | None = typer.Option(None, "--account-id", help="Account/page/author id"),
    visibility: str | None = typer.Option(None, "--visibility", help="Visibility level"),
    extra_json: str | None = typer.Option(None, "--extra-json", help="Provider-specific JSON"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Create a social post.

    Examples:
        ait-social post create --platform twitter --text "Hello world"
        ait-social post create --platform facebook --account-id <page_id> --text "Update"
        ait-social post create --platform instagram --account-id <ig_id> --media-url https://... --text "Caption"
    """

    start = command_timer()
    try:
        settings = load_settings()
        extra: dict[str, object] | None = None
        if extra_json:
            parsed = json.loads(extra_json)
            if not isinstance(parsed, dict):
                raise ToolsetError(
                    code=ErrorCode.INVALID_INPUT,
                    message="--extra-json must be a JSON object",
                    exit_code=ExitCode.INVALID_INPUT,
                )
            extra = parsed

        payload = asyncio.run(
            run_create_post(
                settings=settings,
                platform=platform,
                text=text,
                title=title,
                media_url=media_url,
                link_url=link_url,
                account_id=account_id,
                visibility=visibility,
                extra=extra,
            )
        )
        response = make_success_response("ait-social", "post create", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-social", "post create", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@profile_app.command("get")
def profile_get(
    platform: SocialPlatform = typer.Option(..., "--platform", help="Platform name"),
    account_id: str | None = typer.Option(None, "--account-id", help="Account/page/author id"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Fetch profile/account metadata.

    Examples:
        ait-social profile get --platform twitter
        ait-social profile get --platform facebook --account-id <page_id>
    """

    start = command_timer()
    try:
        settings = load_settings()
        payload = asyncio.run(
            run_get_profile(settings=settings, platform=platform, account_id=account_id)
        )
        response = make_success_response("ait-social", "profile get", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-social", "profile get", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


if __name__ == "__main__":
    app()
