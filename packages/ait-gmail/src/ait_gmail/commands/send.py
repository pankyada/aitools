"""Gmail send/reply/forward command handlers."""

from __future__ import annotations

from ait_core.config.settings import AITSettings

from ait_gmail.client import GmailClient
from ait_gmail.scopes import SCOPES_FULL, SCOPES_SEND


async def run_compose(settings: AITSettings, to: str, subject: str, body: str) -> dict[str, object]:
    """Compose and send a new email.

    Args:
        settings: Loaded settings.
        to: Recipient address list.
        subject: Message subject.
        body: Message body text.

    Returns:
        Gmail send payload.

    Raises:
        ToolsetError: If auth/API fails.
    """

    client = GmailClient(settings=settings, scopes=SCOPES_SEND)
    raw = client.build_mime_message(to=to, subject=subject, body=body)
    return await client.send_message(raw_mime=raw)


async def run_reply(settings: AITSettings, message_id: str, body: str) -> dict[str, object]:
    """Reply to an existing email.

    Args:
        settings: Loaded settings.
        message_id: Source message ID.
        body: Reply content.

    Returns:
        Gmail send payload.

    Raises:
        ToolsetError: If auth/API fails.
    """

    client = GmailClient(settings=settings, scopes=SCOPES_FULL)
    source = await client.get_message(message_id=message_id, fmt="metadata")
    headers = source.payload.get("headers", []) if source.payload else []
    to_addr = ""
    subject = ""
    message_header_id = None
    if isinstance(headers, list):
        for item in headers:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name", "")).lower()
            value = str(item.get("value", ""))
            if name == "from":
                to_addr = value
            elif name == "subject":
                subject = value if value.lower().startswith("re:") else f"Re: {value}"
            elif name == "message-id":
                message_header_id = value

    raw = client.build_mime_message(
        to=to_addr,
        subject=subject or "Re:",
        body=body,
        in_reply_to=message_header_id,
        references=message_header_id,
    )
    return await client.send_message(raw_mime=raw, thread_id=source.thread_id)


async def run_forward(settings: AITSettings, message_id: str, to: str) -> dict[str, object]:
    """Forward an existing message.

    Args:
        settings: Loaded settings.
        message_id: Source message ID.
        to: Forward recipient.

    Returns:
        Gmail send payload.

    Raises:
        ToolsetError: If auth/API fails.
    """

    client = GmailClient(settings=settings, scopes=SCOPES_FULL)
    source = await client.get_message(message_id=message_id, fmt="full")
    subject = "Fwd: (forwarded message)"
    body = source.body_text or source.snippet or ""
    raw = client.build_mime_message(to=to, subject=subject, body=body)
    return await client.send_message(raw_mime=raw)
