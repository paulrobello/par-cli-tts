"""Error handling utilities for PAR CLI TTS."""

import sys
from enum import Enum
from typing import NoReturn

from rich.console import Console

console = Console(stderr=True)


class ErrorType(Enum):
    """Types of errors for consistent handling."""

    # User errors (exit code 1)
    INVALID_INPUT = (1, "Invalid Input")
    FILE_NOT_FOUND = (1, "File Not Found")
    INVALID_VOICE = (1, "Invalid Voice")
    MISSING_API_KEY = (1, "Missing API Key")
    INVALID_PROVIDER = (1, "Invalid Provider")

    # System errors (exit code 2)
    NETWORK_ERROR = (2, "Network Error")
    API_ERROR = (2, "API Error")
    PROVIDER_ERROR = (2, "Provider Error")

    # File system errors (exit code 3)
    PERMISSION_ERROR = (3, "Permission Denied")
    DISK_FULL = (3, "Disk Full")
    WRITE_ERROR = (3, "Write Error")

    # Configuration errors (exit code 4)
    CONFIG_ERROR = (4, "Configuration Error")
    CACHE_ERROR = (4, "Cache Error")

    def __init__(self, exit_code: int, display_name: str):
        """Initialize error type with exit code and display name."""
        self.exit_code = exit_code
        self.display_name = display_name


class TTSError(Exception):
    """Base exception for PAR CLI TTS errors."""

    def __init__(self, message: str, error_type: ErrorType = ErrorType.PROVIDER_ERROR):
        """Initialize TTS error with message and type."""
        self.message = message
        self.error_type = error_type
        super().__init__(self.message)


def handle_error(
    message: str,
    error_type: ErrorType = ErrorType.PROVIDER_ERROR,
    exception: Exception | None = None,
    exit_on_error: bool = True,
) -> NoReturn | None:
    """Handle errors consistently across the application.

    Args:
        message: User-friendly error message.
        error_type: Type of error for categorization.
        exception: Optional exception for debug mode.
        exit_on_error: Whether to exit the program.

    Returns:
        None if exit_on_error is False, otherwise exits.
    """
    # Format error message with type prefix
    error_prefix = f"[red]❌ {error_type.display_name}:[/red]"
    console.print(f"{error_prefix} {message}")

    # Show exception details in debug mode if available
    if exception and hasattr(sys, "_debug_mode") and sys._debug_mode:  # type: ignore
        console.print(f"[dim]Debug: {type(exception).__name__}: {exception}[/dim]")

    if exit_on_error:
        sys.exit(error_type.exit_code)

    return None


def validate_api_key(api_key: str | None, provider: str) -> None:
    """Validate that API key exists for providers that require it.

    Args:
        api_key: API key to validate.
        provider: Provider name.

    Raises:
        TTSError: If API key is missing for providers that require it.
    """
    # Kokoro ONNX doesn't need API key
    if provider == "kokoro-onnx":
        return

    if not api_key:
        handle_error(
            f"API key required for {provider}. Set environment variable or check .env file.", ErrorType.MISSING_API_KEY
        )


def validate_file_path(file_path: str, must_exist: bool = True) -> None:
    """Validate file path for security and existence.

    Args:
        file_path: Path to validate.
        must_exist: Whether file must exist.

    Raises:
        TTSError: If path is invalid or doesn't exist when required.
    """
    from pathlib import Path

    path = Path(file_path)

    # Check for directory traversal attempts
    try:
        path = path.resolve()
    except Exception as e:
        handle_error(f"Invalid file path: {file_path}", ErrorType.INVALID_INPUT, exception=e)

    if must_exist and not path.exists():
        handle_error(f"File not found: {file_path}", ErrorType.FILE_NOT_FOUND)


def wrap_provider_error(func):
    """Decorator to wrap provider errors consistently.

    Args:
        func: Function to wrap.

    Returns:
        Wrapped function with error handling.
    """
    from functools import wraps

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except TTSError:
            # Re-raise our own errors
            raise
        except Exception as e:
            # Wrap other exceptions
            provider_name = getattr(args[0], "name", "Provider") if args else "Provider"
            handle_error(f"{provider_name} error: {str(e)}", ErrorType.PROVIDER_ERROR, exception=e)

    return wrapper
