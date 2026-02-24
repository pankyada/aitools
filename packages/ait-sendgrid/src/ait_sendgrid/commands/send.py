"""SendGrid send/read command handlers."""

from __future__ import annotations

from pathlib import Path

from ait_core.config.settings import AITSettings
from ait_core.errors import ErrorCode, ExitCode, ToolsetError

from ait_sendgrid.client import SendGridClient
from ait_sendgrid.models import SendGridEmailRequest


def resolve_content(
    text: str | None,
    text_file: Path | None,
    html: str | None,
    html_file: Path | None,
) -> tuple[str | None, str | None]:
    """Resolve email content from text/html sources.

    Args:
        text: Plain-text content.
        text_file: Path to plain-text file.
        html: HTML content.
        html_file: Path to HTML file.

    Returns:
        Tuple of `(text, html)`.

    Raises:
        ToolsetError: If no content is provided.
    """

    resolved_text = text or (text_file.read_text(encoding="utf-8") if text_file else None)
    resolved_html = html or (html_file.read_text(encoding="utf-8") if html_file else None)

    if not resolved_text and not resolved_html:
        raise ToolsetError(
            code=ErrorCode.INVALID_INPUT,
            message="Provide at least one of --text, --text-file, --html, or --html-file",
            exit_code=ExitCode.INVALID_INPUT,
        )

    return resolved_text, resolved_html


async def run_send(
    settings: AITSettings,
    to: list[str],
    subject: str,
    from_email: str,
    text: str | None,
    html: str | None,
    cc: list[str],
    bcc: list[str],
    reply_to: str | None,
) -> dict[str, object]:
    """Send email through SendGrid.

    Args:
        settings: Loaded settings.
        to: Recipients.
        subject: Subject line.
        from_email: Sender address.
        text: Plain-text content.
        html: HTML content.
        cc: CC recipients.
        bcc: BCC recipients.
        reply_to: Reply-to address.

    Returns:
        Send response payload.

    Raises:
        ToolsetError: If API call fails.
    """

    client = SendGridClient(settings=settings)
    request = SendGridEmailRequest(
        from_email=from_email,
        to=to,
        subject=subject,
        text=text,
        html=html,
        cc=cc,
        bcc=bcc,
        reply_to=reply_to,
    )
    return await client.send_email(request)


async def run_account(settings: AITSettings) -> dict[str, object]:
    """Get authenticated account metadata.

    Args:
        settings: Loaded settings.

    Returns:
        Account payload.

    Raises:
        ToolsetError: If API call fails.
    """

    client = SendGridClient(settings=settings)
    return await client.get_account()


async def run_unsubscribes(settings: AITSettings, limit: int) -> dict[str, object]:
    """List unsubscribes.

    Args:
        settings: Loaded settings.
        limit: Max results.

    Returns:
        Unsubscribe payload.

    Raises:
        ToolsetError: If API call fails.
    """

    client = SendGridClient(settings=settings)
    return await client.list_unsubscribes(limit=limit)
