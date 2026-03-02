"""Shared pytest fixtures for PAR CLI TTS tests."""

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


@pytest.fixture
def mock_env_api_keys(monkeypatch):
    """Set mock API keys in environment."""
    monkeypatch.setenv("ELEVENLABS_API_KEY", "test_elevenlabs_key_12345")
    monkeypatch.setenv("OPENAI_API_KEY", "test_openai_key_12345")
    monkeypatch.setenv("KOKORO_VOICE_ID", "af_sarah")


@pytest.fixture
def temp_cache_dir(tmp_path):
    """Create a temporary cache directory."""
    cache_dir = tmp_path / "cache"
    cache_dir.mkdir()
    return cache_dir


@pytest.fixture
def temp_config_dir(tmp_path):
    """Create a temporary config directory."""
    config_dir = tmp_path / "config"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def temp_audio_file(tmp_path):
    """Create a temporary audio file for testing."""
    audio_path = tmp_path / "test_audio.mp3"
    audio_path.write_bytes(b"fake audio data")
    return audio_path


@pytest.fixture
def sample_voice_data():
    """Sample voice data for testing."""
    return {
        "voice_id_12345678901234567890": {
            "name": "Test Voice",
            "labels": ["english", "female"],
            "category": "cloned",
        },
        "another_voice_id_123456789012": {
            "name": "Another Voice",
            "labels": ["english", "male"],
            "category": "premade",
        },
    }


@pytest.fixture
def mock_elevenlabs_client():
    """Create a mock ElevenLabs client."""
    client = MagicMock()

    # Mock voices.get_all response
    mock_voice1 = MagicMock()
    mock_voice1.voice_id = "voice_id_12345678901234567890"
    mock_voice1.name = "Rachel"
    mock_voice1.labels = {"accent": "american", "gender": "female"}
    mock_voice1.category = "premade"

    mock_voice2 = MagicMock()
    mock_voice2.voice_id = "another_voice_id_123456789012"
    mock_voice2.name = "Drew"
    mock_voice2.labels = {"accent": "american", "gender": "male"}
    mock_voice2.category = "premade"

    mock_response = MagicMock()
    mock_response.voices = [mock_voice1, mock_voice2]

    client.voices.get_all.return_value = mock_response

    return client


@pytest.fixture
def mock_openai_client():
    """Create a mock OpenAI client."""
    client = MagicMock()

    # Mock audio.speech.create response
    mock_response = MagicMock()
    mock_response.content = b"fake audio data"

    client.audio.speech.create.return_value = mock_response

    return client
