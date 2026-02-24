"""Resend send/read command handlers."""

from __future__ import annotations

from pathlib import Path

from ait_core.config.settings import AITSettings
from ait_core.errors import ErrorCode, ExitCode, ToolsetError

from ait_resend.client import ResendClient
from ait_resend.models import ResendEmailRequest


def resolve_content(
    text: str | None,
    text_file: Path | None,
    html: str | None,
    html_file: Path | None,
) -> tuple[str | None, str | None]:
    """Resolve message content from direct values/files.

    Args:
        text: Plain-text body.
        text_file: Path to plain-text body.
        html: HTML body.
        html_file: Path to HTML body.

    Returns:
        Tuple of `(text, html)`.

    Raises:
        ToolsetError: If no body content is provided.
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
    """Send transactional email using Resend.

    Args:
        settings: Loaded settings.
        to: Recipient email list.
        subject: Message subject.
        from_email: Sender email.
        text: Plain-text body.
        html: HTML body.
        cc: CC recipients.
        bcc: BCC recipients.
        reply_to: Reply-to address.

    Returns:
        Send response payload.

    Raises:
        ToolsetError: If API request fails.
    """

    client = ResendClient(settings=settings)
    request = ResendEmailRequest(
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


async def run_list(settings: AITSettings, limit: int) -> dict[str, object]:
    """List sent emails from Resend.

    Args:
        settings: Loaded settings.
        limit: Max items.

    Returns:
        List response payload.

    Raises:
        ToolsetError: If API request fails.
    """

    client = ResendClient(settings=settings)
    return await client.list_emails(limit=limit)


async def run_get(settings: AITSettings, email_id: str) -> dict[str, object]:
    """Get sent email by id.

    Args:
        settings: Loaded settings.
        email_id: Resend email ID.

    Returns:
        Email payload.

    Raises:
        ToolsetError: If API request fails.
    """

    client = ResendClient(settings=settings)
    return await client.get_email(email_id)
