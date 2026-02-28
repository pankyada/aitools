"""Shared error types and exit-code mappings."""

from __future__ import annotations

from dataclasses import dataclass
from enum import IntEnum, StrEnum


class ExitCode(IntEnum):
    """Process exit codes used by all CLIs."""

    SUCCESS = 0
    GENERAL_ERROR = 1
    AUTH_ERROR = 2
    PERMISSION_ERROR = 3
    NOT_FOUND = 4
    RATE_LIMITED = 5
    INVALID_INPUT = 6


class ErrorCode(StrEnum):
    """Machine-readable error code identifiers."""

    GENERAL_ERROR = "GENERAL_ERROR"
    AUTH_ERROR = "AUTH_ERROR"
    AUTH_EXPIRED = "AUTH_EXPIRED"
    PERMISSION_ERROR = "PERMISSION_ERROR"
    NOT_FOUND = "NOT_FOUND"
    RATE_LIMITED = "RATE_LIMITED"
    INVALID_INPUT = "INVALID_INPUT"
    NETWORK_ERROR = "NETWORK_ERROR"
    CONFIRMATION_REQUIRED = "CONFIRMATION_REQUIRED"


@dataclass(slots=True)
class ToolsetError(Exception):
    """Custom error type used for typed failures in all packages.

    Args:
        code: Machine-readable error code.
        message: Human-readable failure description.
        exit_code: Process exit code for CLI processes.
        details: Optional structured details for debugging/consumers.
        recovery_hints: Optional ordered list of actionable fix suggestions.

    Returns:
        None.

    Raises:
        None.
    """

    code: ErrorCode
    message: str
    exit_code: ExitCode = ExitCode.GENERAL_ERROR
    details: dict[str, object] | None = None
    recovery_hints: list[str] | None = None

    def to_payload(self) -> dict[str, object]:
        """Serialize the error to JSON-compatible dict.

        Args:
            None.

        Returns:
            A dictionary compatible with command response payloads.

        Raises:
            None.
        """

        payload: dict[str, object] = {"code": self.code.value, "message": self.message}
        if self.details:
            payload["details"] = self.details
        if self.recovery_hints:
            payload["hints"] = self.recovery_hints
        return payload
