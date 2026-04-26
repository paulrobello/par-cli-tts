"""Logging configuration helpers for PAR CLI TTS."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

_VALID_LOG_LEVELS = {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG", "NOTSET"}


class JsonLogFormatter(logging.Formatter):
    """Format logging records as single-line JSON objects."""

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True)


def normalize_log_level(level: str) -> str:
    """Return an upper-case log level or raise ValueError for invalid input."""
    normalized = level.upper()
    if normalized not in _VALID_LOG_LEVELS:
        raise ValueError(f"Unknown log level '{level}'. Valid: {', '.join(sorted(_VALID_LOG_LEVELS))}")
    return normalized


def configure_logging(*, structured: bool = False, level: str = "WARNING") -> None:
    """Configure process logging for CLI execution.

    Args:
        structured: When True, emit JSON log records for automation systems.
        level: Standard Python logging level name.
    """
    normalized_level = normalize_log_level(level)
    handler = logging.StreamHandler(sys.stderr)
    if structured:
        handler.setFormatter(JsonLogFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(levelname)s:%(name)s:%(message)s"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(normalized_level)
