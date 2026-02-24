"""Google Drive REST API wrapper."""

from __future__ import annotations

import json
import mimetypes
import uuid
from pathlib import Path
from typing import Any

import httpx
from ait_core.auth.google_auth import GoogleAuthClient
from ait_core.config.settings import AITSettings
from ait_core.errors import ErrorCode, ExitCode, ToolsetError
from ait_core.http.retry import request_with_retry

from ait_gdrive.models import DriveFile
from ait_gdrive.scopes import SCOPES_READ

BASE_URL = "https://www.googleapis.com/drive/v3"
UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3"

GOOGLE_EXPORTS = {
    "application/vnd.google-apps.document": "application/pdf",
    "application/vnd.google-apps.spreadsheet": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    "application/vnd.google-apps.presentation": "application/vnd.openxmlformats-officedocument.presentationml.presentation",
}


class DriveClient:
    """Google Drive API client.

    Args:
        settings: Loaded settings.
        scopes: OAuth scopes.
        http_client: Optional HTTP client.

    Returns:
        None.

    Raises:
        ToolsetError: If auth/API fails.
    """

    def __init__(
        self,
        settings: AITSettings,
        scopes: list[str] | None = None,
        http_client: httpx.AsyncClient | None = None,
    ) -> None:
        self.settings = settings
        self.scopes = scopes or SCOPES_READ
        self.http_client = http_client or httpx.AsyncClient(timeout=90)
        self.auth = GoogleAuthClient(settings=settings)

    async def _headers(self, content_type: str | None = None) -> dict[str, str]:
        """Build auth headers.

        Args:
            content_type: Optional content-type override.

        Returns:
            Header dictionary.

        Raises:
            ToolsetError: If token retrieval fails.
        """

        token = await self.auth.get_valid_access_token(self.scopes)
        headers = {"Authorization": f"Bearer {token}"}
        if content_type:
            headers["Content-Type"] = content_type
        return headers

    async def _request(self, method: str, path: str, **kwargs: Any) -> dict[str, Any]:
        """Execute Drive request and parse JSON body.

        Args:
            method: HTTP method.
            path: API path under base URL.
            **kwargs: Forwarded request args.

        Returns:
            Parsed JSON dictionary.

        Raises:
            ToolsetError: If request fails.
        """

        headers = kwargs.pop("headers", {})
        merged_headers = {**(await self._headers()), **headers}
        response = await request_with_retry(
            self.http_client,
            method,
            f"{BASE_URL}/{path.lstrip('/')}",
            headers=merged_headers,
            **kwargs,
        )
        if response.status_code >= 400:
            self._raise_http_error(response)

        if response.text:
            parsed = response.json()
            if isinstance(parsed, dict):
                return parsed
        return {}

    def _to_file(self, payload: dict[str, Any]) -> DriveFile:
        """Convert API payload to normalized file model.

        Args:
            payload: Drive API object.

        Returns:
            Normalized `DriveFile`.

        Raises:
            KeyError: If required fields are missing.
        """

        owners_raw = payload.get("owners") or []
        owners = [
            str(owner.get("emailAddress") or owner.get("displayName") or "")
            for owner in owners_raw
            if isinstance(owner, dict)
        ]
        return DriveFile(
            id=payload["id"],
            name=payload["name"],
            mime_type=payload.get("mimeType", "application/octet-stream"),
            size=int(payload["size"]) if payload.get("size") else None,
            modified_time=payload.get("modifiedTime"),
            created_time=payload.get("createdTime"),
            parents=payload.get("parents", []),
            owners=owners,
            web_view_link=payload.get("webViewLink"),
        )

    async def list_files(
        self,
        parent_id: str | None = None,
        max_results: int = 100,
        query: str | None = None,
    ) -> dict[str, Any]:
        """List files under an optional folder.

        Args:
            parent_id: Optional parent folder ID.
            max_results: Max files returned.
            query: Additional query expression.

        Returns:
            File list payload.

        Raises:
            ToolsetError: If API fails.
        """

        q_parts = ["trashed = false"]
        if parent_id:
            q_parts.append(f"'{parent_id}' in parents")
        if query:
            q_parts.append(f"({query})")

        payload = await self._request(
            "GET",
            "/files",
            params={
                "q": " and ".join(q_parts),
                "pageSize": max_results,
                "fields": "nextPageToken,files(id,name,mimeType,size,modifiedTime,createdTime,parents,owners,emailAddress,webViewLink)",
            },
        )
        files = payload.get("files", [])
        normalized = [self._to_file(item).model_dump() for item in files if isinstance(item, dict)]
        return {"files": normalized, "next_page_token": payload.get("nextPageToken")}

    async def get_file(self, file_id: str) -> dict[str, Any]:
        """Fetch file metadata by ID.

        Args:
            file_id: Drive file ID.

        Returns:
            File metadata payload.

        Raises:
            ToolsetError: If API fails.
        """

        return await self._request(
            "GET",
            f"/files/{file_id}",
            params={
                "fields": "id,name,mimeType,size,modifiedTime,createdTime,parents,owners,emailAddress,webViewLink",
            },
        )

    async def resolve_path(self, path_value: str) -> str:
        """Resolve user path to Drive file ID by walking path segments.

        Args:
            path_value: Drive path like `Projects/2026/report.pdf`.

        Returns:
            Resolved file ID.

        Raises:
            ToolsetError: If path cannot be resolved.
        """

        clean = path_value.strip("/")
        if not clean:
            return "root"

        parts = clean.split("/")
        parent = "root"
        for part in parts:
            escaped = part.replace("'", "\\'")
            payload = await self.list_files(
                parent_id=parent,
                max_results=200,
                query=f"name = '{escaped}'",
            )
            matches = payload.get("files", [])
            if not matches:
                raise ToolsetError(
                    code=ErrorCode.NOT_FOUND,
                    message=f"Path component not found: {part}",
                    exit_code=ExitCode.NOT_FOUND,
                )
            parent = str(matches[0]["id"])
        return parent

    async def download_file(self, file_id: str, destination: Path | None = None) -> dict[str, Any]:
        """Download file bytes, exporting Google-native files when needed.

        Args:
            file_id: File ID.
            destination: Optional destination path.

        Returns:
            Download payload with path and metadata.

        Raises:
            ToolsetError: If download fails.
        """

        metadata = await self.get_file(file_id)
        mime_type = str(metadata.get("mimeType", ""))
        name = str(metadata.get("name", file_id))

        if mime_type in GOOGLE_EXPORTS:
            export_mime = GOOGLE_EXPORTS[mime_type]
            url = f"{BASE_URL}/files/{file_id}/export"
            params = {"mimeType": export_mime}
            suffix = {
                "application/pdf": ".pdf",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": ".xlsx",
                "application/vnd.openxmlformats-officedocument.presentationml.presentation": ".pptx",
            }.get(export_mime, "")
            if destination is None:
                destination = Path.cwd() / f"{name}{suffix}"
        else:
            url = f"{BASE_URL}/files/{file_id}"
            params = {"alt": "media"}
            if destination is None:
                destination = Path.cwd() / name

        response = await request_with_retry(
            self.http_client,
            "GET",
            url,
            headers=await self._headers(),
            params=params,
        )
        if response.status_code >= 400:
            self._raise_http_error(response)

        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(response.content)

        return {
            "id": file_id,
            "name": name,
            "mime_type": mime_type,
            "saved_to": str(destination),
            "size_bytes": len(response.content),
        }

    async def create_folder(self, name: str, parent: str | None = None) -> dict[str, Any]:
        """Create a Drive folder.

        Args:
            name: Folder name.
            parent: Optional parent folder ID.

        Returns:
            Created folder metadata.

        Raises:
            ToolsetError: If creation fails.
        """

        payload: dict[str, Any] = {
            "name": name,
            "mimeType": "application/vnd.google-apps.folder",
        }
        if parent:
            payload["parents"] = [parent]

        return await self._request("POST", "/files", json=payload)

    async def upload_file(
        self, local_path: Path, name: str | None = None, parent: str | None = None
    ) -> dict[str, Any]:
        """Upload local file with multipart request.

        Args:
            local_path: Source file path.
            name: Optional remote filename.
            parent: Optional parent folder ID.

        Returns:
            Uploaded file metadata.

        Raises:
            ToolsetError: If upload fails.
        """

        if not local_path.exists():
            raise ToolsetError(
                code=ErrorCode.NOT_FOUND,
                message=f"Local file not found: {local_path}",
                exit_code=ExitCode.NOT_FOUND,
            )

        boundary = f"ai-toolset-{uuid.uuid4().hex}"
        meta: dict[str, Any] = {"name": name or local_path.name}
        if parent:
            meta["parents"] = [parent]

        mime = mimetypes.guess_type(local_path.name)[0] or "application/octet-stream"
        file_bytes = local_path.read_bytes()

        body = (
            (
                f"--{boundary}\r\n"
                "Content-Type: application/json; charset=UTF-8\r\n\r\n"
                f"{json.dumps(meta)}\r\n"
                f"--{boundary}\r\n"
                f"Content-Type: {mime}\r\n\r\n"
            ).encode()
            + file_bytes
            + f"\r\n--{boundary}--\r\n".encode()
        )

        response = await request_with_retry(
            self.http_client,
            "POST",
            f"{UPLOAD_URL}/files",
            params={"uploadType": "multipart"},
            headers=await self._headers(content_type=f"multipart/related; boundary={boundary}"),
            content=body,
        )
        if response.status_code >= 400:
            self._raise_http_error(response)

        payload = response.json()
        if not isinstance(payload, dict):
            return {}
        return payload

    async def update_file(
        self,
        file_id: str,
        local_path: Path | None = None,
        rename: str | None = None,
    ) -> dict[str, Any]:
        """Update file metadata and/or content.

        Args:
            file_id: Target file ID.
            local_path: Optional replacement file content.
            rename: Optional new filename.

        Returns:
            Updated file metadata.

        Raises:
            ToolsetError: If update fails.
        """

        if local_path is None:
            if rename is None:
                raise ToolsetError(
                    code=ErrorCode.INVALID_INPUT,
                    message="Provide --file or --rename",
                    exit_code=ExitCode.INVALID_INPUT,
                )
            return await self._request("PATCH", f"/files/{file_id}", json={"name": rename})

        mime = mimetypes.guess_type(local_path.name)[0] or "application/octet-stream"
        data = local_path.read_bytes()
        response = await request_with_retry(
            self.http_client,
            "PATCH",
            f"{UPLOAD_URL}/files/{file_id}",
            params={"uploadType": "media"},
            headers=await self._headers(content_type=mime),
            content=data,
        )
        if response.status_code >= 400:
            self._raise_http_error(response)

        payload = response.json()
        if not isinstance(payload, dict):
            return {}

        if rename:
            await self._request("PATCH", f"/files/{file_id}", json={"name": rename})
        return payload

    async def delete_file(self, file_id: str, permanent: bool = False) -> dict[str, Any]:
        """Trash or permanently delete a file.

        Args:
            file_id: Target file ID.
            permanent: Whether to permanently remove.

        Returns:
            Action payload.

        Raises:
            ToolsetError: If delete fails.
        """

        if permanent:
            await self._request("DELETE", f"/files/{file_id}")
            return {"deleted": True, "file_id": file_id, "permanent": True}

        await self._request("PATCH", f"/files/{file_id}", json={"trashed": True})
        return {"deleted": True, "file_id": file_id, "permanent": False}

    async def search(self, query: str, max_results: int = 50) -> dict[str, Any]:
        """Search files via Drive query syntax.

        Args:
            query: Query string.
            max_results: Maximum results.

        Returns:
            Search payload.

        Raises:
            ToolsetError: If search fails.
        """

        return await self.list_files(max_results=max_results, query=query)

    def _raise_http_error(self, response: httpx.Response) -> None:
        """Raise typed tool error from HTTP status.

        Args:
            response: HTTP response.

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
            message=f"Drive API request failed ({response.status_code})",
            exit_code=exit_code,
            details={"body": response.text},
        )
