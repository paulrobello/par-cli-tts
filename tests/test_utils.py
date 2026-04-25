"""Tests for utility functions."""

from pathlib import Path

from par_cli_tts.utils import (
    calculate_file_checksum,
    looks_like_voice_id,
    sanitize_debug_output,
    stream_to_file,
    verify_file_checksum,
)


class TestLooksLikeVoiceId:
    """Tests for looks_like_voice_id function."""

    def test_short_name_returns_false(self):
        """Short names should not be detected as voice IDs."""
        assert looks_like_voice_id("Rachel") is False
        assert looks_like_voice_id("voice") is False
        assert looks_like_voice_id("test") is False

    def test_long_alphanumeric_returns_true(self):
        """Long alphanumeric strings should be detected as voice IDs."""
        assert looks_like_voice_id("abcdefghij1234567890") is True
        assert looks_like_voice_id("VoiceID1234567890123456") is True

    def test_id_with_underscores_returns_true(self):
        """Voice IDs with underscores should be detected."""
        assert looks_like_voice_id("voice_id_12345678901234") is True
        assert looks_like_voice_id("aMSt68OGf4xUZAnLpTU8") is True

    def test_name_with_spaces_returns_false(self):
        """Names with spaces should not be detected as voice IDs."""
        assert looks_like_voice_id("This is a voice name") is False
        assert looks_like_voice_id("Test Voice Name Here") is False

    def test_custom_min_length(self):
        """Should respect custom minimum length."""
        assert looks_like_voice_id("short", min_length=5) is True
        assert looks_like_voice_id("short", min_length=10) is False


class TestSanitizeDebugOutput:
    """Tests for sanitize_debug_output function."""

    def test_masks_api_keys(self):
        """API keys should be masked in output."""
        data = {"API_KEY": "secret123", "OTHER": "value"}
        result = sanitize_debug_output(data)
        assert result["API_KEY"] == "***REDACTED***"
        assert result["OTHER"] == "value"

    def test_masks_tokens(self):
        """Tokens should be masked in output."""
        data = {"TOKEN": "mytoken123", "DATA": "info"}
        result = sanitize_debug_output(data)
        assert result["TOKEN"] == "***REDACTED***"
        assert result["DATA"] == "info"

    def test_masks_secrets(self):
        """Secrets should be masked in output."""
        data = {"SECRET": "shhh", "PUBLIC": "hello"}
        result = sanitize_debug_output(data)
        assert result["SECRET"] == "***REDACTED***"
        assert result["PUBLIC"] == "hello"

    def test_masks_long_alphanumeric_values(self):
        """Long alphanumeric strings that look like keys should be masked."""
        data = {"data": "abcdefghij12345678901234567890abcdef"}
        result = sanitize_debug_output(data)
        assert result["data"] == "***POSSIBLE_KEY_REDACTED***"

    def test_handles_nested_dicts(self):
        """Should recursively sanitize nested dictionaries."""
        data = {"outer": {"API_KEY": "secret", "value": "normal"}}
        result = sanitize_debug_output(data)
        assert result["outer"]["API_KEY"] == "***REDACTED***"
        assert result["outer"]["value"] == "normal"


class TestChecksumFunctions:
    """Tests for checksum functions."""

    def test_calculate_checksum(self, tmp_path):
        """Should calculate correct SHA256 checksum."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        checksum = calculate_file_checksum(test_file)
        assert len(checksum) == 64  # SHA256 produces 64 hex chars
        assert checksum.isalnum()

    def test_verify_checksum_matches(self, tmp_path):
        """Should return True for matching checksums."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        checksum = calculate_file_checksum(test_file)
        assert verify_file_checksum(test_file, checksum) is True

    def test_verify_checksum_mismatch(self, tmp_path):
        """Should return False for mismatched checksums."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("test content")

        fake_checksum = "0" * 64
        assert verify_file_checksum(test_file, fake_checksum) is False

    def test_verify_checksum_missing_file(self, tmp_path):
        """Should return False for missing files."""
        missing_file = tmp_path / "missing.txt"
        assert verify_file_checksum(missing_file, "checksum") is False


class TestStreamToFile:
    """Tests for stream_to_file function."""

    def test_writes_chunks_to_file(self, tmp_path):
        """Should write all chunks to the output file."""
        output_file = tmp_path / "output.bin"
        chunks = [b"chunk1", b"chunk2", b"chunk3"]

        stream_to_file(iter(chunks), output_file)

        assert output_file.exists()
        assert output_file.read_bytes() == b"chunk1chunk2chunk3"

    def test_writes_to_existing_subdirectory(self, tmp_path):
        """Should write to file in existing subdirectory."""
        subdir = tmp_path / "subdir"
        subdir.mkdir()
        output_file = subdir / "output.bin"
        chunks = [b"data"]

        stream_to_file(iter(chunks), output_file)

        assert output_file.exists()
        assert output_file.read_bytes() == b"data"
