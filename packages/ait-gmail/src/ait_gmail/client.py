"""Gmail REST API wrapper using Google OAuth access tokens."""

from __future__ import annotations

import base64
import email.utils
from datetime import date
from email.message import EmailMessage
from typing import Any

import httpx
from ait_core.auth.google_auth import GoogleAuthClient
from ait_core.config.settings import AITSettings
from ait_core.errors import ErrorCode, ExitCode, ToolsetError
from ait_core.http.retry import request_with_retry

from ait_gmail.models import EmailAddress, MessageFull, MessageSummary
from ait_gmail.scopes import SCOPES_FULL, SCOPES_MODIFY, SCOPES_READ, SCOPES_SEND

BASE_URL = "https://gmail.googleapis.com/gmail/v1/users/me"


class GmailClient:
    """Gmail API client.

    Args:
        settings: Loaded toolset settings.
        scopes: OAuth scopes required for this client.
        http_client: Optional HTTP client.

    Returns:
        None.

    Raises:
        ToolsetError: If auth or API calls fail.
    """

    def __init__(
        self,
        settings: AITSettings,
        scopes: list[str] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self.scopes = scopes or SCOPES_READ
        self.http_client = http_client or httpx.AsyncClient(timeout=45)
        self.auth = GoogleAuthClient(settings=settings)

    async def _headers(self) -> dict[str, str]:
        """Build auth headers.

        Args:
            None.

        Returns:
            Request headers.

        Raises:
            ToolsetError: If token retrieval fails.
        """

        token = await self.auth.get_valid_access_token(self.scopes)
        return {"Authorization": f"Bearer {token}"}

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Execute Gmail API request and parse JSON body.

        Args:
            method: HTTP method.
            path: API path under base URL.
            **kwargs: Forwarded request args.

        Returns:
            Parsed JSON payload.

        Raises:
            ToolsetError: If request fails.
        """

        response = await request_with_retry(
            self.http_client,
            method,
            f"{BASE_URL}/{path.lstrip('/')}",
            headers=await self._headers(),
            **kwargs,
        )

        if response.status_code >= 400:
            self._raise_http_error(response)

        if response.text:
            parsed = response.json()
            if isinstance(parsed, dict):
                return parsed
        return {}

    @staticmethod
    def _parse_address(raw: str | None) -> EmailAddress:
        """Parse RFC2822 address string into name/email.

        Args:
            raw: Header value.

        Returns:
            Parsed address model.

        Raises:
            None.
        """

        name, addr = email.utils.parseaddr(raw or "")
        return EmailAddress(name=name or None, email=addr or "")

    @staticmethod
    def _header_value(headers: list[dict[str, str]], name: str) -> str | None:
        """Find header value by key.

        Args:
            headers: Header list from Gmail payload.
            name: Header key.

        Returns:
            Header value or None.

        Raises:
            None.
        """

        needle = name.lower()
        for header in headers:
            if header.get("name", "").lower() == needle:
                return header.get("value")
        return None

    @staticmethod
    def _has_attachments(payload: dict[str, Any]) -> bool:
        """Detect whether Gmail payload includes attachments.

        Args:
            payload: Message payload.

        Returns:
            True when any part indicates an attachment.

        Raises:
            None.
        """

        parts = payload.get("parts") or []
        if not isinstance(parts, list):
            return False

        def walk(items: list[dict[str, Any]]) -> bool:
            for part in items:
                if part.get("filename"):
                    return True
                subparts = part.get("parts")
                if isinstance(subparts, list) and walk(
                    [p for p in subparts if isinstance(p, dict)]
                ):
                    return True
            return False

        return walk([item for item in parts if isinstance(item, dict)])

    @staticmethod
    def _extract_body(payload: dict[str, Any]) -> str:
        """Extract plaintext/HTML body as text.

        Args:
            payload: Gmail message payload.

        Returns:
            Decoded body text.

        Raises:
            ValueError: If body payload is malformed base64.
        """

        def decode_data(data: str | None) -> str:
            if not data:
                return ""
            raw = data.replace("-", "+").replace("_", "/")
            pad = len(raw) % 4
            if pad:
                raw += "=" * (4 - pad)
            return base64.b64decode(raw.encode("utf-8")).decode("utf-8", errors="replace")

        body = payload.get("body", {})
        if isinstance(body, dict) and body.get("data"):
            return decode_data(body.get("data"))

        parts = payload.get("parts") or []
        for part in parts:
            if not isinstance(part, dict):
                continue
            mime = part.get("mimeType", "")
            if mime in {"text/plain", "text/html"}:
                part_body = part.get("body", {})
                if isinstance(part_body, dict):
                    text = decode_data(part_body.get("data"))
                    if text:
                        return text
        return ""

    def _to_summary(self, message: dict[str, Any]) -> MessageSummary:
        """Convert Gmail message payload to normalized summary.

        Args:
            message: Gmail message payload.

        Returns:
            Parsed message summary model.

        Raises:
            KeyError: If required fields are missing.
        """

        payload = message.get("payload", {})
        headers = payload.get("headers", []) if isinstance(payload, dict) else []
        if not isinstance(headers, list):
            headers = []

        from_raw = self._header_value(headers, "From")
        to_raw = self._header_value(headers, "To")
        subject = self._header_value(headers, "Subject")
        date_value = self._header_value(headers, "Date")

        recipients: list[EmailAddress] = []
        if to_raw:
            for name, addr in email.utils.getaddresses([to_raw]):
                recipients.append(EmailAddress(name=name or None, email=addr))

        return MessageSummary(
            id=message["id"],
            thread_id=message["threadId"],
            from_=self._parse_address(from_raw),
            to=recipients,
            subject=subject,
            snippet=message.get("snippet"),
            date=date_value,
            labels=message.get("labelIds", []),
            has_attachments=self._has_attachments(payload if isinstance(payload, dict) else {}),
            size_bytes=message.get("sizeEstimate"),
        )

    async def list_messages(
        self,
        label: str = "INBOX",
        max_results: int = 20,
        unread: bool = False,
        after: date | None = None,
        before: date | None = None,
        from_filter: str | None = None,
        has_attachment: bool = False,
        page_token: str | None = None,
    ) -> dict[str, Any]:
        """List Gmail messages and return normalized summaries.

        Args:
            label: Gmail label filter.
            max_results: Maximum count.
            unread: Restrict to unread messages.
            after: Lower date bound.
            before: Upper date bound.
            from_filter: Sender filter.
            has_attachment: Restrict to messages with attachments.
            page_token: Next-page token.

        Returns:
            Message list payload with pagination info.

        Raises:
            ToolsetError: If API call fails.
        """

        query_parts: list[str] = []
        if unread:
            query_parts.append("is:unread")
        if after:
            query_parts.append(f"after:{after.isoformat()}")
        if before:
            query_parts.append(f"before:{before.isoformat()}")
        if from_filter:
            query_parts.append(f"from:{from_filter}")
        if has_attachment:
            query_parts.append("has:attachment")

        params: dict[str, Any] = {
            "labelIds": label,
            "maxResults": max_results,
            "q": " ".join(query_parts).strip(),
        }
        if page_token:
            params["pageToken"] = page_token

        listing = await self._request("GET", "/messages", params=params)
        refs = listing.get("messages", [])
        summaries: list[dict[str, Any]] = []

        for ref in refs:
            if not isinstance(ref, dict) or "id" not in ref:
                continue
            msg = await self._request("GET", f"/messages/{ref['id']}", params={"format": "full"})
            summaries.append(self._to_summary(msg).model_dump(by_alias=True))

        return {
            "messages": summaries,
            "total_estimate": listing.get("resultSizeEstimate", len(summaries)),
            "next_page_token": listing.get("nextPageToken"),
        }

    async def get_message(self, message_id: str, fmt: str = "full") -> MessageFull:
        """Get a single Gmail message.

        Args:
            message_id: Gmail message ID.
            fmt: Gmail API format value.

        Returns:
            Parsed message payload.

        Raises:
            ToolsetError: If message fetch fails.
        """

        payload = await self._request("GET", f"/messages/{message_id}", params={"format": fmt})
        body_text = None
        if fmt in {"full", "raw"}:
            raw_payload = payload.get("payload")
            if isinstance(raw_payload, dict):
                body_text = self._extract_body(raw_payload)

        return MessageFull(
            id=payload["id"],
            thread_id=payload["threadId"],
            snippet=payload.get("snippet"),
            labels=payload.get("labelIds", []),
            internal_date=int(payload.get("internalDate", 0))
            if payload.get("internalDate")
            else None,
            payload=payload.get("payload"),
            body_text=body_text,
        )

    async def search_messages(self, query: str, max_results: int = 20) -> dict[str, Any]:
        """Search Gmail messages by query string.

        Args:
            query: Gmail search query.
            max_results: Maximum results.

        Returns:
            Message list payload.

        Raises:
            ToolsetError: If API call fails.
        """

        listing = await self._request(
            "GET",
            "/messages",
            params={"q": query, "maxResults": max_results},
        )
        refs = listing.get("messages", [])
        messages: list[dict[str, Any]] = []
        for ref in refs:
            if not isinstance(ref, dict) or "id" not in ref:
                continue
            msg = await self._request("GET", f"/messages/{ref['id']}", params={"format": "full"})
            messages.append(self._to_summary(msg).model_dump(by_alias=True))

        return {
            "messages": messages,
            "total_estimate": listing.get("resultSizeEstimate", len(messages)),
            "next_page_token": listing.get("nextPageToken"),
        }

    async def get_thread(self, thread_id: str) -> dict[str, Any]:
        """Fetch a Gmail thread and summarize contained messages.

        Args:
            thread_id: Gmail thread ID.

        Returns:
            Thread payload containing message summaries.

        Raises:
            ToolsetError: If API call fails.
        """

        payload = await self._request("GET", f"/threads/{thread_id}", params={"format": "full"})
        messages = payload.get("messages", [])
        summaries = [
            self._to_summary(msg).model_dump(by_alias=True)
            for msg in messages
            if isinstance(msg, dict)
        ]
        return {"thread_id": thread_id, "messages": summaries}

    async def send_message(self, raw_mime: str, thread_id: str | None = None) -> dict[str, Any]:
        """Send message with RFC822 raw MIME payload.

        Args:
            raw_mime: Base64url encoded MIME message.
            thread_id: Optional thread for reply context.

        Returns:
            Gmail API send response payload.

        Raises:
            ToolsetError: If send fails.
        """

        body: dict[str, Any] = {"raw": raw_mime}
        if thread_id:
            body["threadId"] = thread_id
        return await self._request("POST", "/messages/send", json=body)

    @staticmethod
    def build_mime_message(
        to: str,
        subject: str,
        body: str,
        cc: str | None = None,
        in_reply_to: str | None = None,
        references: str | None = None,
    ) -> str:
        """Create base64url MIME payload for Gmail send endpoint.

        Args:
            to: Recipient email list.
            subject: Message subject.
            body: Body text.
            cc: Optional cc value.
            in_reply_to: Optional message ID for reply threading.
            references: Optional references header value.

        Returns:
            Base64url MIME string.

        Raises:
            None.
        """

        msg = EmailMessage()
        msg["To"] = to
        msg["Subject"] = subject
        if cc:
            msg["Cc"] = cc
        if in_reply_to:
            msg["In-Reply-To"] = in_reply_to
        if references:
            msg["References"] = references
        msg.set_content(body)

        encoded = base64.urlsafe_b64encode(msg.as_bytes()).decode("utf-8")
        return encoded.rstrip("=")

    async def trash_messages(self, message_ids: list[str]) -> dict[str, Any]:
        """Move messages to trash.

        Args:
            message_ids: Message IDs.

        Returns:
            Action summary.

        Raises:
            ToolsetError: If operation fails.
        """

        for message_id in message_ids:
            await self._request("POST", f"/messages/{message_id}/trash")
        return {"trashed": len(message_ids), "message_ids": message_ids}

    async def delete_messages(self, message_ids: list[str]) -> dict[str, Any]:
        """Permanently delete messages.

        Args:
            message_ids: Message IDs.

        Returns:
            Action summary.

        Raises:
            ToolsetError: If operation fails.
        """

        for message_id in message_ids:
            await self._request("DELETE", f"/messages/{message_id}")
        return {"deleted": len(message_ids), "message_ids": message_ids}

    def _raise_http_error(self, response: httpx.Response) -> None:
        """Raise typed errors from Gmail HTTP status.

        Args:
            response: HTTP error response.

        Returns:
            None.

        Raises:
            ToolsetError: Always raised.
        """

        code = ErrorCode.GENERAL_ERROR
        exit_code = ExitCode.GENERAL_ERROR
        if response.status_code in {401, 403}:
            code = ErrorCode.AUTH_ERROR
            exit_code = ExitCode.AUTH_ERROR
        elif response.status_code == 404:
            code = ErrorCode.NOT_FOUND
            exit_code = ExitCode.NOT_FOUND
        elif response.status_code == 429:
            code = ErrorCode.RATE_LIMITED
            exit_code = ExitCode.RATE_LIMITED

        raise ToolsetError(
            code=code,
            message=f"Gmail API request failed ({response.status_code})",
            exit_code=exit_code,
            details={"body": response.text},
        )


def default_scopes_for_action(action: str) -> list[str]:
    """Resolve required scopes by action category.

    Args:
        action: One of `read`, `send`, `modify`, `full`.

    Returns:
        Required scope list.

    Raises:
        ValueError: If action is unknown.
    """

    if action == "read":
        return SCOPES_READ
    if action == "send":
        return SCOPES_SEND
    if action == "modify":
        return SCOPES_MODIFY
    if action == "full":
        return SCOPES_FULL
    raise ValueError(f"Unknown action scope: {action}")
