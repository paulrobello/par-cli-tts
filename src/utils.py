"""Utility functions for PAR CLI TTS."""

import hashlib
import subprocess
import sys
import tempfile
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


def looks_like_voice_id(identifier: str, min_length: int = 20) -> bool:
    """Check if identifier looks like a voice ID rather than a name.

    Voice IDs are typically long alphanumeric strings, while voice names
    are shorter and may contain spaces or special characters.

    Args:
        identifier: The string to check.
        min_length: Minimum length to consider as a potential voice ID.
            Defaults to 20 characters.

    Returns:
        True if the identifier appears to be a voice ID, False otherwise.
    """
    return len(identifier) >= min_length and identifier.replace("_", "").isalnum()


def play_audio_with_player(file_path: Path, volume: float = 1.0) -> None:
    """Play audio using system player with volume support.

    This function detects the operating system and uses the appropriate
    audio player with volume control support.

    Args:
        file_path: Path to the audio file to play.
        volume: Volume level (0.0 = silent, 1.0 = normal, 2.0 = double).

    Raises:
        RuntimeError: If no suitable audio player is found on Linux.
    """
    if sys.platform == "darwin":  # macOS
        # afplay supports volume flag (-v)
        subprocess.run(["afplay", "-v", str(volume), str(file_path)], check=True)
    elif sys.platform == "win32":  # Windows
        # Windows doesn't have native volume control for start command
        subprocess.run(["start", "", str(file_path)], shell=True, check=True)
    else:  # Linux and others
        # Try common audio players with volume support
        players_with_volume = [
            ("paplay", ["--volume", str(int(volume * 65536))]),  # paplay uses 0-65536
            ("ffplay", ["-volume", str(int(volume * 100)), "-nodisp", "-autoexit"]),  # ffplay uses 0-100
            ("mpg123", ["-f", str(int(volume * 32768))]),  # mpg123 uses scale factor
            ("aplay", []),  # aplay doesn't support volume directly
        ]

        for player, volume_args in players_with_volume:
            try:
                cmd = [player] + volume_args + [str(file_path)]
                subprocess.run(cmd, check=True)
                return
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        raise RuntimeError("No audio player found. Install aplay, paplay, ffplay, or mpg123.")


def play_audio_bytes(audio_data: bytes, volume: float = 1.0, suffix: str = ".mp3") -> None:
    """Play audio data from bytes using system player.

    This is a convenience function that saves audio bytes to a temporary
    file and plays it using the system audio player.

    Args:
        audio_data: Audio data as bytes.
        volume: Volume level (0.0 = silent, 1.0 = normal, 2.0 = double).
        suffix: File suffix for temporary file (default: .mp3).
    """
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_data)
        tmp_path = Path(tmp.name)

    try:
        play_audio_with_player(tmp_path, volume)
    finally:
        # Clean up temp file
        if tmp_path.exists():
            tmp_path.unlink()
