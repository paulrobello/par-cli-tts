"""Error handling utilities for PAR CLI TTS."""

import logging
import sys
from enum import Enum
from typing import NoReturn

_logger = logging.getLogger(__name__)


class ErrorType(Enum):
    """Types of errors for consistent handling."""

    INVALID_INPUT = (1, "Invalid Input")
    FILE_NOT_FOUND = (1, "File Not Found")
    INVALID_VOICE = (1, "Invalid Voice")
    MISSING_API_KEY = (1, "Missing API Key")
    INVALID_PROVIDER = (1, "Invalid Provider")

    NETWORK_ERROR = (2, "Network Error")
    API_ERROR = (2, "API Error")
    PROVIDER_ERROR = (2, "Provider Error")

    PERMISSION_ERROR = (3, "Permission Denied")
    DISK_FULL = (3, "Disk Full")
    WRITE_ERROR = (3, "Write Error")

    CONFIG_ERROR = (4, "Configuration Error")
    CACHE_ERROR = (4, "Cache Error")

    def __init__(self, exit_code: int, display_name: str):
        self.exit_code = exit_code
        self.display_name = display_name


class TTSError(Exception):
    """Base exception for PAR CLI TTS errors."""

    def __init__(self, message: str, error_type: ErrorType = ErrorType.PROVIDER_ERROR):
        self.message = message
        self.error_type = error_type
        super().__init__(self.message)


def handle_error(
    message: str,
    error_type: ErrorType = ErrorType.PROVIDER_ERROR,
    exception: Exception | None = None,
    exit_on_error: bool = False,
) -> NoReturn:
    """Log an error and raise TTSError (or sys.exit in legacy mode).

    In library mode (default), raises TTSError so callers can catch and handle
    errors programmatically.  When *exit_on_error* is True the process calls
    ``sys.exit()`` instead -- this is retained for the CLI layer's use.

    Args:
        message: Human-readable error description.
        error_type: Categorised error type carrying an exit-code.
        exception: Optional original exception for debug logging.
        exit_on_error: If True, call ``sys.exit()`` instead of raising.

    Raises:
        TTSError: Always, unless *exit_on_error* is True.
    """
    _logger.error("%s: %s", error_type.display_name, message)

    if exception and hasattr(sys, "_debug_mode") and sys._debug_mode:  # type: ignore
        _logger.debug("Debug: %s: %s", type(exception).__name__, exception)

    if exit_on_error:
        sys.exit(error_type.exit_code)

    raise TTSError(message, error_type)


def validate_api_key(api_key: str | None, provider: str) -> None:
    if provider == "kokoro-onnx":
        return

    if not api_key:
        handle_error(
            f"API key required for {provider}. Set environment variable or check .env file.",
            ErrorType.MISSING_API_KEY,
        )


def validate_file_path(file_path: str, must_exist: bool = True) -> None:
    from pathlib import Path

    path = Path(file_path)

    try:
        path = path.resolve()
    except Exception as e:
        handle_error(f"Invalid file path: {file_path}", ErrorType.INVALID_INPUT, exception=e)

    if must_exist and not path.exists():
        handle_error(f"File not found: {file_path}", ErrorType.FILE_NOT_FOUND)


def wrap_provider_error(func):
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TTSError:
            raise
        except Exception as e:
            provider_name = getattr(args[0], "name", "Provider") if args else "Provider"
            handle_error(f"{provider_name} error: {str(e)}", ErrorType.PROVIDER_ERROR, exception=e)

    return wrapper
