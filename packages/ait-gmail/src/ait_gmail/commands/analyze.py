"""Gmail analysis command handlers."""

from __future__ import annotations

from collections import Counter
from datetime import UTC, datetime, timedelta
from typing import Any

from ait_core.config.settings import AITSettings
from ait_core.errors import ToolsetError

from ait_gmail.client import GmailClient
from ait_gmail.scopes import SCOPES_READ


def _sender_email(message: dict[str, object]) -> str:
    """Extract sender email from summary payload.

    Args:
        message: Gmail summary payload.

    Returns:
        Sender email or empty string.

    Raises:
        None.
    """

    raw = message.get("from_")
    if isinstance(raw, dict):
        email = raw.get("email")
        if isinstance(email, str):
            return email
    return ""


def _subject_text(message: dict[str, object]) -> str:
    """Extract subject from summary payload.

    Args:
        message: Gmail summary payload.

    Returns:
        Subject text.

    Raises:
        None.
    """

    subject = message.get("subject")
    return subject if isinstance(subject, str) else ""


def _has_unread_label(message: dict[str, object]) -> bool:
    """Check whether summary includes UNREAD label.

    Args:
        message: Gmail summary payload.

    Returns:
        True if UNREAD label exists.

    Raises:
        None.
    """

    labels = message.get("labels")
    if not isinstance(labels, list):
        return False
    return any(isinstance(label, str) and label == "UNREAD" for label in labels)


def _as_int(value: object) -> int:
    """Convert scalar-like value to integer.

    Args:
        value: Candidate value.

    Returns:
        Integer conversion or zero.

    Raises:
        None.
    """

    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(float(value))
        except ValueError:
            return 0
    return 0


def get_llm_client(settings: AITSettings) -> Any | None:
    """Return xAI client if available and configured.

    Args:
        settings: Loaded settings.

    Returns:
        XAIClient instance or None.

    Raises:
        None.
    """

    try:
        from ait_xai.client import XAIClient

        return XAIClient(settings=settings)
    except Exception:
        return None


async def _fetch_window_messages(
    settings: AITSettings, days: int, label: str
) -> list[dict[str, object]]:
    """Fetch recent messages for analysis window.

    Args:
        settings: Loaded settings.
        days: Time window in days.
        label: Label filter.

    Returns:
        Message summaries.

    Raises:
        ToolsetError: If API fails.
    """

    client = GmailClient(settings=settings, scopes=SCOPES_READ)
    since = (datetime.now(tz=UTC) - timedelta(days=days)).date()
    payload = await client.list_messages(label=label, max_results=200, after=since)
    return [m for m in payload.get("messages", []) if isinstance(m, dict)]


async def run_summary(
    settings: AITSettings, days: int, label: str, use_llm: bool
) -> dict[str, object]:
    """Summarize recent email activity.

    Args:
        settings: Loaded settings.
        days: Window in days.
        label: Label filter.
        use_llm: Prefer LLM summarization when available.

    Returns:
        Summary payload.

    Raises:
        ToolsetError: If message fetch fails.
    """

    messages = await _fetch_window_messages(settings=settings, days=days, label=label)
    senders = Counter(_sender_email(message) for message in messages if _sender_email(message))

    if use_llm:
        llm_client = get_llm_client(settings)
        if llm_client is not None:
            lines = [
                f"From: {_sender_email(m)} | Subject: {_subject_text(m)}" for m in messages[:100]
            ]
            prompt = "\n".join(lines)
            try:
                from ait_xai.models import ChatMessage, ChatRequest

                chat = await llm_client.chat(
                    ChatRequest(
                        model=settings.xai.default_model,
                        messages=[
                            ChatMessage(
                                role="system",
                                content="Summarize this inbox sample by urgency and action items.",
                            ),
                            ChatMessage(role="user", content=prompt),
                        ],
                        temperature=0.2,
                    )
                )
                return {
                    "mode": "llm",
                    "summary": chat.content,
                    "message_count": len(messages),
                    "top_senders": senders.most_common(10),
                }
            except ToolsetError:
                pass

    return {
        "mode": "stats",
        "window_days": days,
        "label": label,
        "message_count": len(messages),
        "top_senders": senders.most_common(10),
    }


async def run_stats(settings: AITSettings, days: int) -> dict[str, object]:
    """Compute inbox statistics.

    Args:
        settings: Loaded settings.
        days: Window in days.

    Returns:
        Stats payload.

    Raises:
        ToolsetError: If message fetch fails.
    """

    messages = await _fetch_window_messages(settings=settings, days=days, label="INBOX")
    unread = sum(1 for m in messages if _has_unread_label(m))
    attachments = sum(1 for m in messages if bool(m.get("has_attachments")))
    return {
        "window_days": days,
        "message_count": len(messages),
        "unread_count": unread,
        "attachment_count": attachments,
    }


async def run_senders(settings: AITSettings, top: int, days: int) -> dict[str, object]:
    """Compute top sender list.

    Args:
        settings: Loaded settings.
        top: Top sender count.
        days: Window in days.

    Returns:
        Sender frequency payload.

    Raises:
        ToolsetError: If message fetch fails.
    """

    messages = await _fetch_window_messages(settings=settings, days=days, label="INBOX")
    senders = Counter(_sender_email(message) for message in messages if _sender_email(message))
    return {"window_days": days, "top": top, "senders": senders.most_common(top)}


async def run_threads(settings: AITSettings, unresolved: bool, days: int) -> dict[str, object]:
    """Analyze thread activity.

    Args:
        settings: Loaded settings.
        unresolved: Filter unresolved heuristics.
        days: Window in days.

    Returns:
        Thread list payload.

    Raises:
        ToolsetError: If message fetch fails.
    """

    messages = await _fetch_window_messages(settings=settings, days=days, label="INBOX")
    thread_counts = Counter(str(m.get("thread_id", "")) for m in messages)
    candidates = [
        {"thread_id": thread_id, "count": count}
        for thread_id, count in thread_counts.most_common()
        if thread_id
    ]
    if unresolved:
        candidates = [c for c in candidates if _as_int(c["count"]) >= 2]
    return {"window_days": days, "unresolved_only": unresolved, "threads": candidates[:50]}
