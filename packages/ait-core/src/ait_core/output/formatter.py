"""Response envelope and rendering helpers shared by all CLIs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from time import perf_counter
from typing import Any, Literal

from rich.console import Console
from rich.panel import Panel
from rich.pretty import Pretty
from rich.text import Text

from ait_core.errors import ToolsetError

OutputMode = Literal["json", "rich", "plain"]


@dataclass(slots=True)
class CommandResponse:
    """Standard response envelope.

    Args:
        success: Whether command execution was successful.
        data: Command-specific payload object.
        metadata: Tool/command/timing metadata.
        error: Optional error payload.

    Returns:
        None.

    Raises:
        None.
    """

    success: bool
    data: dict[str, Any] | list[Any] | None
    metadata: dict[str, Any]
    error: dict[str, Any] | None

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary.

        Args:
            None.

        Returns:
            Serialized envelope dictionary.

        Raises:
            None.
        """

        return {
            "success": self.success,
            "data": self.data,
            "metadata": self.metadata,
            "error": self.error,
        }


def command_timer() -> float:
    """Return a monotonic start timestamp for duration measurements.

    Args:
        None.

    Returns:
        Floating-point perf-counter value.

    Raises:
        None.
    """

    return perf_counter()


def make_metadata(tool: str, command: str, start: float) -> dict[str, Any]:
    """Build command metadata object.

    Args:
        tool: Tool identifier.
        command: Command identifier.
        start: Start time from `command_timer`.

    Returns:
        Metadata object following shared output contract.

    Raises:
        None.
    """

    execution_ms = int((perf_counter() - start) * 1000)
    return {
        "tool": tool,
        "command": command,
        "timestamp": datetime.now(tz=UTC).isoformat().replace("+00:00", "Z"),
        "execution_ms": execution_ms,
    }


def make_success_response(
    tool: str, command: str, data: dict[str, Any] | list[Any], start: float
) -> CommandResponse:
    """Create successful response envelope.

    Args:
        tool: Tool identifier.
        command: Command identifier.
        data: Command payload.
        start: Start timer value.

    Returns:
        Successful `CommandResponse`.

    Raises:
        None.
    """

    return CommandResponse(
        success=True,
        data=data,
        metadata=make_metadata(tool, command, start),
        error=None,
    )


def make_error_response(
    tool: str,
    command: str,
    start: float,
    error: ToolsetError | Exception,
) -> CommandResponse:
    """Create failure response envelope.

    Args:
        tool: Tool identifier.
        command: Command identifier.
        start: Start timer value.
        error: Raised exception.

    Returns:
        Failed `CommandResponse`.

    Raises:
        None.
    """

    if isinstance(error, ToolsetError):
        payload = error.to_payload()
    else:
        payload = {"code": "GENERAL_ERROR", "message": str(error)}

    return CommandResponse(
        success=False,
        data=None,
        metadata=make_metadata(tool, command, start),
        error=payload,
    )


def _format_plain(response: CommandResponse) -> str:
    """Create plain text response.

    Args:
        response: Envelope to render.

    Returns:
        Plain string rendering.

    Raises:
        None.
    """

    lines: list[str] = [f"success\t{response.success}"]
    if response.error:
        for key, value in response.error.items():
            if key == "hints" and isinstance(value, list):
                for i, hint in enumerate(value):
                    lines.append(f"error_hint_{i + 1}\t{hint}")
            else:
                lines.append(f"error_{key}\t{value}")

    if isinstance(response.data, dict):
        for key, value in response.data.items():
            lines.append(f"{key}\t{value}")
    elif isinstance(response.data, list):
        lines.append(f"items\t{len(response.data)}")

    return "\n".join(lines)


def _render_rich_error(
    rich_console: Console, response: CommandResponse
) -> None:
    """Render an error response with hints in rich format.

    Args:
        rich_console: Rich console to print to.
        response: Failed command response.

    Returns:
        None.

    Raises:
        None.
    """

    error = response.error or {}
    message = error.get("message", "An unexpected error occurred")
    hints: list[str] = error.get("hints", [])  # type: ignore[assignment]

    body = Text()
    body.append("✗ ", style="bold red")
    body.append(str(message), style="red")

    if hints:
        body.append("\n\n")
        body.append("💡 How to fix:\n", style="bold yellow")
        for i, hint in enumerate(hints, 1):
            body.append(f"   {i}. {hint}\n", style="yellow")

    rich_console.print(Panel(body, title="[bold red]Error[/bold red]", border_style="red"))


def format_output(
    response: CommandResponse, mode: OutputMode, console: Console | None = None
) -> str:
    """Render response in selected output mode.

    Args:
        response: Envelope to render.
        mode: Output mode (`json`, `rich`, or `plain`).
        console: Optional rich console for rich mode printing.

    Returns:
        A rendered string when mode is `json` or `plain`; empty string for rich mode.

    Raises:
        ValueError: If output mode is unsupported.
    """

    if mode == "json":
        return json.dumps(response.to_dict(), ensure_ascii=False)
    if mode == "plain":
        return _format_plain(response)
    if mode == "rich":
        rich_console = console or Console()
        if not response.success:
            _render_rich_error(rich_console, response)
        else:
            rich_console.print(Panel(Pretty(response.to_dict()), title="[bold green]Success[/bold green]", border_style="green"))
        return ""
    raise ValueError(f"Unsupported output mode: {mode}")
