"""Google Calendar REST API wrapper."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx
from ait_core.auth.google_auth import GoogleAuthClient
from ait_core.config.settings import AITSettings
from ait_core.errors import ErrorCode, ExitCode, ToolsetError
from ait_core.http.retry import request_with_retry

from ait_gcal.models import CalendarItem, EventItem
from ait_gcal.scopes import SCOPES_READ

BASE_URL = "https://www.googleapis.com/calendar/v3"


class GCalClient:
    """Google Calendar API client.

    Args:
        settings: Loaded settings.
        scopes: OAuth scopes for this client.
        http_client: Optional async HTTP client.

    Returns:
        None.

    Raises:
        ToolsetError: If auth/api operations fail.
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
            Header dictionary with bearer token.

        Raises:
            ToolsetError: If token retrieval fails.
        """

        token = await self.auth.get_valid_access_token(self.scopes)
        return {"Authorization": f"Bearer {token}"}

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Execute Calendar request and parse JSON object.

        Args:
            method: HTTP method.
            path: API path under BASE_URL.
            **kwargs: Forwarded request kwargs.

        Returns:
            Parsed JSON object.

        Raises:
            ToolsetError: If API call fails.
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

        if not response.text:
            return {}
        payload = response.json()
        if isinstance(payload, dict):
            return payload
        return {}

    async def list_calendars(self, max_results: int = 100) -> dict[str, object]:
        """List accessible calendars.

        Args:
            max_results: Maximum returned calendars.

        Returns:
            Calendar list payload.

        Raises:
            ToolsetError: If API call fails.
        """

        payload = await self._request(
            "GET",
            "/users/me/calendarList",
            params={"maxResults": max_results},
        )
        items = payload.get("items", [])
        calendars = []
        for item in items:
            if not isinstance(item, dict):
                continue
            model = CalendarItem(
                id=str(item.get("id", "")),
                summary=item.get("summary"),
                description=item.get("description"),
                timezone=item.get("timeZone"),
                primary=bool(item.get("primary", False)),
            )
            calendars.append(model.model_dump(exclude_none=True))

        return {
            "calendars": calendars,
            "next_page_token": payload.get("nextPageToken"),
        }

    async def list_events(
        self,
        calendar_id: str,
        max_results: int = 20,
        time_min: str | None = None,
        time_max: str | None = None,
        query: str | None = None,
    ) -> dict[str, object]:
        """List events in a calendar.

        Args:
            calendar_id: Calendar id (e.g., `primary`).
            max_results: Maximum number of events.
            time_min: Optional RFC3339 lower bound.
            time_max: Optional RFC3339 upper bound.
            query: Optional search term.

        Returns:
            Event list payload.

        Raises:
            ToolsetError: If API call fails.
        """

        params: dict[str, object] = {
            "maxResults": max_results,
            "singleEvents": True,
            "orderBy": "startTime",
        }
        if time_min:
            params["timeMin"] = time_min
        if time_max:
            params["timeMax"] = time_max
        if query:
            params["q"] = query

        cal = quote(calendar_id, safe="")
        payload = await self._request("GET", f"/calendars/{cal}/events", params=params)
        items = payload.get("items", [])
        events = []
        for item in items:
            if not isinstance(item, dict):
                continue
            events.append(self._to_event(item).model_dump(exclude_none=True))

        return {
            "calendar_id": calendar_id,
            "events": events,
            "next_page_token": payload.get("nextPageToken"),
        }

    async def get_event(self, calendar_id: str, event_id: str) -> dict[str, object]:
        """Get a single event by id.

        Args:
            calendar_id: Calendar id.
            event_id: Event id.

        Returns:
            Event payload.

        Raises:
            ToolsetError: If API call fails.
        """

        cal = quote(calendar_id, safe="")
        event = quote(event_id, safe="")
        payload = await self._request("GET", f"/calendars/{cal}/events/{event}")
        return self._to_event(payload).model_dump(exclude_none=True)

    async def create_event(
        self,
        calendar_id: str,
        summary: str,
        start: str,
        end: str,
        description: str | None = None,
        location: str | None = None,
        timezone: str | None = None,
    ) -> dict[str, object]:
        """Create a calendar event.

        Args:
            calendar_id: Calendar id.
            summary: Event summary/title.
            start: RFC3339 start datetime.
            end: RFC3339 end datetime.
            description: Optional description.
            location: Optional location.
            timezone: Optional timezone.

        Returns:
            Created event payload.

        Raises:
            ToolsetError: If API call fails.
        """

        body: dict[str, object] = {
            "summary": summary,
            "start": {"dateTime": start},
            "end": {"dateTime": end},
        }
        if description:
            body["description"] = description
        if location:
            body["location"] = location
        if timezone:
            body["start"] = {"dateTime": start, "timeZone": timezone}
            body["end"] = {"dateTime": end, "timeZone": timezone}

        cal = quote(calendar_id, safe="")
        payload = await self._request("POST", f"/calendars/{cal}/events", json=body)
        return self._to_event(payload).model_dump(exclude_none=True)

    async def delete_event(self, calendar_id: str, event_id: str) -> dict[str, object]:
        """Delete an event.

        Args:
            calendar_id: Calendar id.
            event_id: Event id.

        Returns:
            Delete result payload.

        Raises:
            ToolsetError: If API call fails.
        """

        cal = quote(calendar_id, safe="")
        event = quote(event_id, safe="")
        await self._request("DELETE", f"/calendars/{cal}/events/{event}")
        return {"deleted": True, "calendar_id": calendar_id, "event_id": event_id}

    @staticmethod
    def normalize_rfc3339(value: str) -> str:
        """Normalize user datetime string to RFC3339.

        Args:
            value: Input datetime string.

        Returns:
            RFC3339 datetime string.

        Raises:
            ToolsetError: If format is invalid.
        """

        text = value.strip()
        if not text:
            raise ToolsetError(
                code=ErrorCode.INVALID_INPUT,
                message="Datetime value cannot be empty",
                exit_code=ExitCode.INVALID_INPUT,
            )

        if text.endswith("Z"):
            text = text[:-1] + "+00:00"

        try:
            parsed = datetime.fromisoformat(text)
        except ValueError as exc:
            raise ToolsetError(
                code=ErrorCode.INVALID_INPUT,
                message="Invalid datetime format. Use ISO8601/RFC3339.",
                exit_code=ExitCode.INVALID_INPUT,
            ) from exc

        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=UTC)

        return parsed.isoformat().replace("+00:00", "Z")

    @staticmethod
    def _to_event(item: dict[str, Any]) -> EventItem:
        """Normalize Google event payload.

        Args:
            item: Raw event object.

        Returns:
            Normalized event model.

        Raises:
            None.
        """

        start_raw = item.get("start", {})
        end_raw = item.get("end", {})
        start = None
        end = None

        if isinstance(start_raw, dict):
            start = start_raw.get("dateTime") or start_raw.get("date")
        if isinstance(end_raw, dict):
            end = end_raw.get("dateTime") or end_raw.get("date")

        creator = item.get("creator", {})
        creator_email = creator.get("email") if isinstance(creator, dict) else None

        return EventItem(
            id=str(item.get("id", "")),
            status=item.get("status"),
            summary=item.get("summary"),
            description=item.get("description"),
            location=item.get("location"),
            start=start,
            end=end,
            html_link=item.get("htmlLink"),
            creator_email=creator_email,
        )

    def _raise_http_error(self, response: httpx.Response) -> None:
        """Raise typed error for Calendar HTTP failure.

        Args:
            response: Error response.

        Returns:
            None.

        Raises:
            ToolsetError: Always.
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
            message=f"Google Calendar API request failed ({response.status_code})",
            exit_code=exit_code,
            details={"body": response.text},
        )
