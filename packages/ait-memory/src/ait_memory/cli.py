"""Typer CLI for `ait-memory`."""

from __future__ import annotations

import asyncio
import sys
from datetime import date
from pathlib import Path

import typer
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

from ait_memory.commands.get import run_get
from ait_memory.commands.search import run_search
from ait_memory.commands.store import run_store
from ait_memory.db import MemoryDB

app = typer.Typer(help="Local memory command-line interface")
entities_app = typer.Typer(help="Entity operations")
app.add_typer(entities_app, name="entities")


def _print(mode: OutputMode, response: CommandResponse) -> None:
    """Render and print command response.

    Args:
        mode: Output mode.
        response: Response envelope.

    Returns:
        None.

    Raises:
        None.
    """

    rendered = format_output(response, mode)
    if rendered:
        print(rendered)


def _read_text_input(text: str | None, file: Path | None, stdin: bool) -> str:
    """Resolve input text from one of text/file/stdin.

    Args:
        text: Direct text value.
        file: Optional file path.
        stdin: Read from stdin toggle.

    Returns:
        Resolved content string.

    Raises:
        ToolsetError: If no source is provided.
    """

    if text:
        return text
    if file:
        return file.read_text(encoding="utf-8")
    if stdin:
        data = sys.stdin.read()
        return data.strip()
    raise ToolsetError(
        code=ErrorCode.INVALID_INPUT,
        message="Provide --text, --file, or --stdin",
        exit_code=ExitCode.INVALID_INPUT,
    )


def _parse_date(value: str | None) -> date | None:
    """Parse ISO date.

    Args:
        value: Date string.

    Returns:
        Date or None.

    Raises:
        ValueError: If invalid.
    """

    if value is None:
        return None
    return date.fromisoformat(value)


@app.command("init")
def init(output: OutputMode = typer.Option("json", "--output", "-o")) -> None:
    """Initialize the local memory database.

    Examples:
        ait-memory init
    """

    start = command_timer()
    try:
        settings = load_settings()
        db = MemoryDB(settings)
        db.init_db()
        response = make_success_response(
            "ait-memory",
            "init",
            {"initialized": True, "db_path": str(db.db_path)},
            start,
        )
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-memory", "init", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@app.command("store")
def store(
    text: str | None = typer.Option(None, "--text", help="Memory text"),
    file: Path | None = typer.Option(None, "--file", help="Read content from file"),
    stdin: bool = typer.Option(False, "--stdin", help="Read from stdin"),
    source: str = typer.Option("user", "--source", help="Source label"),
    source_ref: str | None = typer.Option(None, "--source-ref", help="Source reference"),
    importance: float = typer.Option(0.5, "--importance", min=0.0, max=1.0),
    tags: str | None = typer.Option(None, "--tags", help="Comma-separated tags"),
    no_extract: bool = typer.Option(False, "--no-extract", help="Skip entity extraction"),
    no_embed: bool = typer.Option(False, "--no-embed", help="Skip embedding generation"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Store a memory entry.

    Examples:
        ait-memory store --text "Project alpha due Friday" --source user
        cat note.txt | ait-memory store --stdin --source gmail --source-ref msg_123
    """

    _ = tags
    start = command_timer()
    try:
        content = _read_text_input(text=text, file=file, stdin=stdin)
        settings = load_settings()
        payload = asyncio.run(
            run_store(
                settings=settings,
                text=content,
                source=source,
                source_ref=source_ref,
                importance=importance,
                extract=not no_extract,
                embed=not no_embed,
            )
        )
        response = make_success_response("ait-memory", "store", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-memory", "store", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@app.command("get")
def get(
    memory_id: str | None = typer.Argument(None, help="Memory ID"),
    entity: str | None = typer.Option(None, "--entity", help="Entity name"),
    recent: bool = typer.Option(False, "--recent", help="Get recent memories"),
    limit: int = typer.Option(10, "--limit", help="Limit for --recent"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Get memory entries.

    Examples:
        ait-memory get 01H...
        ait-memory get --entity "project alpha"
        ait-memory get --recent --limit 10
    """

    start = command_timer()
    try:
        settings = load_settings()
        payload = asyncio.run(
            run_get(
                settings=settings,
                memory_id=memory_id,
                entity=entity,
                recent=recent,
                limit=limit,
            )
        )
        response = make_success_response("ait-memory", "get", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-memory", "get", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@app.command("search")
def search(
    query: str = typer.Argument(..., help="Search query"),
    semantic: bool = typer.Option(True, "--semantic/--keyword", help="Search mode toggle"),
    hybrid: bool = typer.Option(False, "--hybrid", help="Enable hybrid search"),
    entity: str | None = typer.Option(None, "--entity", help="Entity filter"),
    source: str | None = typer.Option(None, "--source", help="Source filter"),
    after: str | None = typer.Option(None, "--after", help="After date YYYY-MM-DD"),
    before: str | None = typer.Option(None, "--before", help="Before date YYYY-MM-DD"),
    min_importance: float | None = typer.Option(None, "--min-importance", min=0.0, max=1.0),
    limit: int = typer.Option(10, "--limit", help="Max results"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Search memory records.

    Examples:
        ait-memory search "project alpha deadline" --hybrid
        ait-memory search "invoice" --keyword --source gmail
    """

    start = command_timer()
    try:
        settings = load_settings()
        mode = "semantic" if semantic else "keyword"
        payload = asyncio.run(
            run_search(
                settings=settings,
                query=query,
                mode=mode,
                hybrid=hybrid,
                entity=entity,
                source=source,
                after=_parse_date(after),
                before=_parse_date(before),
                min_importance=min_importance,
                limit=limit,
            )
        )
        response = make_success_response("ait-memory", "search", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-memory", "search", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@entities_app.command("list")
def entities_list(
    sort: str = typer.Option("importance", "--sort", help="Sort by importance or recency"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """List entities.

    Examples:
        ait-memory entities list --sort importance
    """

    start = command_timer()
    try:
        db = MemoryDB(load_settings())
        db.init_db()
        payload = {"entities": db.list_entities(sort=sort)}
        response = make_success_response("ait-memory", "entities list", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-memory", "entities list", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@entities_app.command("get")
def entities_get(
    name: str = typer.Argument(..., help="Entity name"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Get one entity.

    Examples:
        ait-memory entities get "project alpha"
    """

    start = command_timer()
    try:
        db = MemoryDB(load_settings())
        db.init_db()
        payload = {"entity": db.get_entity(name)}
        response = make_success_response("ait-memory", "entities get", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-memory", "entities get", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@entities_app.command("relationships")
def entities_relationships(
    name: str = typer.Argument(..., help="Entity name"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Get relationships for an entity.

    Examples:
        ait-memory entities relationships "project alpha"
    """

    start = command_timer()
    try:
        db = MemoryDB(load_settings())
        db.init_db()
        payload = {"relationships": db.get_relationships(name)}
        response = make_success_response("ait-memory", "entities relationships", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-memory", "entities relationships", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@app.command("stats")
def stats(output: OutputMode = typer.Option("json", "--output", "-o")) -> None:
    """Show memory database stats.

    Examples:
        ait-memory stats
    """

    start = command_timer()
    try:
        db = MemoryDB(load_settings())
        db.init_db()
        response = make_success_response("ait-memory", "stats", db.stats(), start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-memory", "stats", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@app.command("forget")
def forget(
    memory_ids: list[str] = typer.Argument(..., help="Memory IDs"),
    confirm: bool = typer.Option(False, "--confirm", help="Required for deletion"),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Delete memories by ID.

    Examples:
        ait-memory forget <id1> <id2> --confirm
    """

    start = command_timer()
    try:
        if not confirm:
            raise ToolsetError(
                code=ErrorCode.CONFIRMATION_REQUIRED,
                message="Forget requires --confirm",
                exit_code=ExitCode.INVALID_INPUT,
                details={"confirmation_token": "FORGET"},
            )
        db = MemoryDB(load_settings())
        db.init_db()
        payload = db.forget(memory_ids)
        response = make_success_response("ait-memory", "forget", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-memory", "forget", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


@app.command("compact")
def compact(
    prune_below: float | None = typer.Option(None, "--prune-below", min=0.0, max=1.0),
    output: OutputMode = typer.Option("json", "--output", "-o"),
) -> None:
    """Recompute importance scores and optionally prune low-value memories.

    Examples:
        ait-memory compact
        ait-memory compact --prune-below 0.1
    """

    start = command_timer()
    try:
        db = MemoryDB(load_settings())
        db.init_db()
        payload = db.compact(prune_threshold=prune_below)
        response = make_success_response("ait-memory", "compact", payload, start)
        _print(output, response)
    except Exception as exc:
        response = make_error_response("ait-memory", "compact", start, exc)
        _print(output, response)
        raise typer.Exit(code=getattr(exc, "exit_code", ExitCode.GENERAL_ERROR)) from exc


if __name__ == "__main__":
    app()
