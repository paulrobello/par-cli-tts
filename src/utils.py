"""Utility functions for PAR CLI TTS."""

import hashlib
from collections.abc import Iterator
from pathlib import Path
from typing import Any, BinaryIO


def stream_to_file(audio_stream: Iterator[bytes], file_path: str | Path) -> None:
    """Stream audio data directly to file without buffering in memory.

    Args:
        audio_stream: Iterator yielding audio data chunks.
        file_path: Path to save the audio file.
    """
    file_path = Path(file_path)
    with open(file_path, "wb") as f:
        for chunk in audio_stream:
            f.write(chunk)


def write_with_stream(file_handle: BinaryIO, audio_stream: Iterator[bytes]) -> None:
    """Write audio stream to an already open file handle.

    Args:
        file_handle: Open binary file handle.
        audio_stream: Iterator yielding audio data chunks.
    """
    for chunk in audio_stream:
        file_handle.write(chunk)


def sanitize_debug_output(data: dict[str, Any]) -> dict[str, Any]:
    """Remove sensitive data from debug output.

    Args:
        data: Dictionary potentially containing sensitive data.

    Returns:
        Sanitized dictionary with sensitive values masked.
    """
    sensitive_keys = ["API_KEY", "TOKEN", "SECRET", "PASSWORD", "KEY", "CREDENTIAL"]
    sanitized = {}

    for key, value in data.items():
        # Check if the key contains any sensitive terms
        if any(term in key.upper() for term in sensitive_keys):
            sanitized[key] = "***REDACTED***"
        elif isinstance(value, dict):
            # Recursively sanitize nested dictionaries
            sanitized[key] = sanitize_debug_output(value)
        elif isinstance(value, str) and len(value) > 20:
            # Check if value looks like an API key (long alphanumeric string)
            if value.replace("-", "").replace("_", "").isalnum() and len(value) > 30:
                sanitized[key] = "***POSSIBLE_KEY_REDACTED***"
            else:
                sanitized[key] = value
        else:
            sanitized[key] = value

    return sanitized


def verify_file_checksum(file_path: Path, expected_checksum: str, algorithm: str = "sha256") -> bool:
    """Verify a file's checksum.

    Args:
        file_path: Path to the file to verify.
        expected_checksum: Expected checksum value.
        algorithm: Hash algorithm to use (default: sha256).

    Returns:
        True if checksum matches, False otherwise.
    """
    if not file_path.exists():
        return False

    hasher = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)

    return hasher.hexdigest() == expected_checksum


def calculate_file_checksum(file_path: Path, algorithm: str = "sha256") -> str:
    """Calculate a file's checksum.

    Args:
        file_path: Path to the file.
        algorithm: Hash algorithm to use (default: sha256).

    Returns:
        Hexadecimal checksum string.
    """
    hasher = hashlib.new(algorithm)
    with open(file_path, "rb") as f:
        while chunk := f.read(8192):
            hasher.update(chunk)

    return hasher.hexdigest()
