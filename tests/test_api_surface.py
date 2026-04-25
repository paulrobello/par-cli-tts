"""Tests for the public API surface of par_tts."""

import pytest


def test_top_level_imports():
    """All public names should be importable from par_tts."""
    from par_tts import (
        TTSProvider,
        Voice,
        SpeechResult,
        ElevenLabsOptions,
        OpenAIOptions,
        KokoroOptions,
        DeepgramOptions,
        GeminiOptions,
        PROVIDERS,
        get_provider,
        list_providers,
    )

    assert isinstance(PROVIDERS, dict)
    assert "elevenlabs" in PROVIDERS
    assert "openai" in PROVIDERS
    assert "kokoro-onnx" in PROVIDERS
    assert "deepgram" in PROVIDERS
    assert "gemini" in PROVIDERS


def test_get_provider_factory():
    """get_provider should return the correct provider class."""
    from par_tts import PROVIDERS, get_provider

    for name, cls in PROVIDERS.items():
        assert get_provider(name) is cls


def test_get_provider_unknown_raises():
    """get_provider with unknown name should raise ValueError."""
    from par_tts import get_provider

    with pytest.raises(ValueError, match="Unknown provider"):
        get_provider("nonexistent")


def test_list_providers():
    """list_providers should return all provider names."""
    from par_tts import list_providers

    names = list_providers()
    assert "elevenlabs" in names
    assert "kokoro-onnx" in names
    assert len(names) == 5


def test_provider_imports():
    """Individual provider classes should be importable."""
    from par_tts.providers import (
        DeepgramProvider,
        ElevenLabsProvider,
        GeminiProvider,
        KokoroONNXProvider,
        OpenAIProvider,
    )


def test_audio_module_importable():
    """Audio playback utilities should be importable."""
    from par_tts.audio import play_audio_bytes, play_audio_with_player


def test_utils_module_importable():
    """Utility functions should be importable."""
    from par_tts.utils import looks_like_voice_id, stream_to_file
