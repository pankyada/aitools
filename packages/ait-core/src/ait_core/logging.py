"""Structured logging setup with structlog."""

from __future__ import annotations

import logging

import structlog


def configure_logging(level: str = "warning") -> None:
    """Configure stdlib and structlog output.

    Args:
        level: Log level as string.

    Returns:
        None.

    Raises:
        ValueError: If level is invalid.
    """

    numeric_level = getattr(logging, level.upper(), None)
    if not isinstance(numeric_level, int):
        raise ValueError(f"Invalid log level: {level}")

    logging.basicConfig(level=numeric_level, format="%(message)s")
    structlog.configure(
        processors=[
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.add_log_level,
            structlog.processors.JSONRenderer(),
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )
