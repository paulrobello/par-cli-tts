"""Tests for voice cache functionality."""

from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from par_tts.utils import looks_like_voice_id


class TestVoiceCache:
    """Tests for VoiceCache class."""

    def test_is_expired_no_timestamp(self, temp_cache_dir, monkeypatch):
        """Cache with no timestamp should be expired."""
        from par_tts.voice_cache import VoiceCache

        monkeypatch.setattr(
            "par_tts.voice_cache.platformdirs.user_cache_dir",
            lambda _: str(temp_cache_dir)
        )

        cache = VoiceCache("test-app")
        cache.cache_data["timestamp"] = None

        assert cache.is_expired() is True

    def test_is_expired_recent_cache(self, temp_cache_dir, monkeypatch):
        """Recent cache should not be expired."""
        from par_tts.voice_cache import VoiceCache

        monkeypatch.setattr(
            "par_tts.voice_cache.platformdirs.user_cache_dir",
            lambda _: str(temp_cache_dir)
        )

        cache = VoiceCache("test-app")
        cache.cache_data["timestamp"] = datetime.now().isoformat()

        assert cache.is_expired() is False

    def test_is_expired_old_cache(self, temp_cache_dir, monkeypatch):
        """Cache older than expiry days should be expired."""
        from par_tts.voice_cache import VoiceCache, CACHE_EXPIRY_DAYS

        monkeypatch.setattr(
            "par_tts.voice_cache.platformdirs.user_cache_dir",
            lambda _: str(temp_cache_dir)
        )

        cache = VoiceCache("test-app")
        old_time = datetime.now() - timedelta(days=CACHE_EXPIRY_DAYS + 1)
        cache.cache_data["timestamp"] = old_time.isoformat()

        assert cache.is_expired() is True

    def test_get_voice_by_name_exact_match(self, temp_cache_dir, monkeypatch, sample_voice_data):
        """Should find voice by exact name match."""
        from par_tts.voice_cache import VoiceCache

        monkeypatch.setattr(
            "par_tts.voice_cache.platformdirs.user_cache_dir",
            lambda _: str(temp_cache_dir)
        )

        cache = VoiceCache("test-app")
        cache.cache_data["voices"] = sample_voice_data
        cache.cache_data["timestamp"] = datetime.now().isoformat()

        result = cache.get_voice_by_name("Test Voice")
        assert result == "voice_id_12345678901234567890"

    def test_get_voice_by_name_partial_match(self, temp_cache_dir, monkeypatch, sample_voice_data):
        """Should find voice by partial name match."""
        from par_tts.voice_cache import VoiceCache

        monkeypatch.setattr(
            "par_tts.voice_cache.platformdirs.user_cache_dir",
            lambda _: str(temp_cache_dir)
        )

        cache = VoiceCache("test-app")
        cache.cache_data["voices"] = sample_voice_data
        cache.cache_data["timestamp"] = datetime.now().isoformat()

        result = cache.get_voice_by_name("Test")
        assert result == "voice_id_12345678901234567890"

    def test_get_voice_by_name_case_insensitive(self, temp_cache_dir, monkeypatch, sample_voice_data):
        """Should find voice with case-insensitive matching."""
        from par_tts.voice_cache import VoiceCache

        monkeypatch.setattr(
            "par_tts.voice_cache.platformdirs.user_cache_dir",
            lambda _: str(temp_cache_dir)
        )

        cache = VoiceCache("test-app")
        cache.cache_data["voices"] = sample_voice_data
        cache.cache_data["timestamp"] = datetime.now().isoformat()

        result = cache.get_voice_by_name("test voice")
        assert result == "voice_id_12345678901234567890"

    def test_get_voice_by_name_expired_cache(self, temp_cache_dir, monkeypatch, sample_voice_data):
        """Should return None for expired cache."""
        from par_tts.voice_cache import VoiceCache

        monkeypatch.setattr(
            "par_tts.voice_cache.platformdirs.user_cache_dir",
            lambda _: str(temp_cache_dir)
        )

        cache = VoiceCache("test-app")
        cache.cache_data["voices"] = sample_voice_data
        cache.cache_data["timestamp"] = None  # Expired

        result = cache.get_voice_by_name("Test Voice")
        assert result is None

    def test_clear_cache(self, temp_cache_dir, monkeypatch):
        """Should clear cache data."""
        from par_tts.voice_cache import VoiceCache

        monkeypatch.setattr(
            "par_tts.voice_cache.platformdirs.user_cache_dir",
            lambda _: str(temp_cache_dir)
        )

        cache = VoiceCache("test-app")
        cache.cache_data["voices"] = {"id": {"name": "test"}}
        cache.cache_data["timestamp"] = datetime.now().isoformat()

        cache.clear_cache()

        assert cache.cache_data["voices"] == {}
        assert cache.cache_data["timestamp"] is None


class TestResolveVoiceIdentifier:
    """Tests for resolve_voice_identifier function."""

    def test_returns_voice_id_unchanged(self, temp_cache_dir, monkeypatch):
        """Should return voice ID unchanged if it looks like an ID."""
        from par_tts.voice_cache import resolve_voice_identifier

        # Voice IDs are 20+ alphanumeric characters
        voice_id = "abcdefghij1234567890"
        result = resolve_voice_identifier(voice_id, MagicMock())
        assert result == voice_id

    def test_resolves_from_cache(self, temp_cache_dir, monkeypatch, mock_elevenlabs_client, sample_voice_data):
        """Should resolve voice name from cache."""
        from par_tts.voice_cache import VoiceCache, resolve_voice_identifier

        monkeypatch.setattr(
            "par_tts.voice_cache.platformdirs.user_cache_dir",
            lambda _: str(temp_cache_dir)
        )

        cache = VoiceCache("test-app")
        cache.cache_data["voices"] = sample_voice_data
        cache.cache_data["timestamp"] = datetime.now().isoformat()

        result = resolve_voice_identifier("Test Voice", mock_elevenlabs_client, cache)

        assert result == "voice_id_12345678901234567890"

    def test_raises_for_ambiguous_name(self, temp_cache_dir, monkeypatch):
        """Should raise ValueError for ambiguous voice names."""
        from par_tts.voice_cache import resolve_voice_identifier

        # Setup mock client with multiple voices matching "Voice"
        client = MagicMock()
        mock_voice1 = MagicMock()
        mock_voice1.voice_id = "id1"
        mock_voice1.name = "Test Voice"

        mock_voice2 = MagicMock()
        mock_voice2.voice_id = "id2"
        mock_voice2.name = "Another Voice"

        mock_response = MagicMock()
        mock_response.voices = [mock_voice1, mock_voice2]
        client.voices.get_all.return_value = mock_response

        with pytest.raises(ValueError) as exc_info:
            resolve_voice_identifier("Voice", client)

        assert "Ambiguous" in str(exc_info.value)


class TestLooksLikeVoiceIdInCache:
    """Tests for voice ID detection in cache context."""

    def test_elevenlabs_voice_id_detected(self):
        """Should detect ElevenLabs voice IDs."""
        assert looks_like_voice_id("aMSt68OGf4xUZAnLpTU8") is True
        assert looks_like_voice_id("21m00Tcm4TlvDq8ikWAM") is True

    def test_voice_name_not_detected(self):
        """Should not detect voice names as IDs."""
        assert looks_like_voice_id("Rachel") is False
        assert looks_like_voice_id("Juniper") is False
        assert looks_like_voice_id("Drew") is False
