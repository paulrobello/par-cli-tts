"""Tests for the public API surface of par_tts."""

import pytest


def test_top_level_imports():
    """All public names should be importable from par_tts."""
    import par_tts

    assert isinstance(par_tts.PROVIDERS, dict)
    assert "elevenlabs" in par_tts.PROVIDERS
    assert "openai" in par_tts.PROVIDERS
    assert "kokoro-onnx" in par_tts.PROVIDERS
    assert "deepgram" in par_tts.PROVIDERS
    assert "gemini" in par_tts.PROVIDERS


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

    assert DeepgramProvider is not None
    assert ElevenLabsProvider is not None
    assert GeminiProvider is not None
    assert KokoroONNXProvider is not None
    assert OpenAIProvider is not None


def test_audio_module_importable():
    """Audio playback utilities should be importable."""
    from par_tts.audio import play_audio_bytes, play_audio_with_player

    assert play_audio_bytes is not None
    assert play_audio_with_player is not None


def test_utils_module_importable():
    """Utility functions should be importable."""
    from par_tts.utils import looks_like_voice_id, stream_to_file

    assert looks_like_voice_id is not None
    assert stream_to_file is not None


def test_compat_shim_par_cli_tts():
    """par_cli_tts should re-export everything from par_tts."""
    import warnings

    # Suppress the deprecation warning for this test
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", DeprecationWarning)
        import par_cli_tts

        assert hasattr(par_cli_tts, "TTSProvider")
        assert hasattr(par_cli_tts, "Voice")
        assert hasattr(par_cli_tts, "get_provider")
        assert hasattr(par_cli_tts, "__version__")

        from par_cli_tts.providers import PROVIDERS as shim_providers
        from par_tts.providers import PROVIDERS

        assert shim_providers is PROVIDERS
