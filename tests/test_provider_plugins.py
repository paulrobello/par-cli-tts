"""Provider plugin registry tests."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

from par_tts.providers.base import TTSProvider, Voice


class FakeEntryPoint:
    """Minimal entry point test double."""

    def __init__(self, name: str, loaded: Any = None, error: Exception | None = None) -> None:
        self.name = name
        self._loaded = loaded
        self._error = error

    def load(self) -> Any:
        if self._error is not None:
            raise self._error
        return self._loaded


class MinimalProvider(TTSProvider):
    """Provider class used to test entry point normalization."""

    plugin_name = "minimal"
    plugin_description = "Minimal provider"
    plugin_capabilities = {
        "formats": ["wav"],
        "supports_speed": True,
        "supports_streaming": False,
        "supports_voice_controls": False,
    }
    plugin_default_model = "minimal-model"
    plugin_requires_api_key = False

    def generate_speech(
        self,
        text: str,
        voice: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> bytes | Iterator[bytes]:
        return b"audio"

    def list_voices(self) -> list[Voice]:
        return [Voice(id="voice", name="Voice")]

    def resolve_voice(self, voice_identifier: str) -> str:
        return voice_identifier

    @property
    def name(self) -> str:
        return "Minimal"

    @property
    def supported_formats(self) -> list[str]:
        return ["wav"]

    @property
    def default_model(self) -> str:
        return "minimal-model"

    @property
    def default_voice(self) -> str:
        return "voice"


def test_builtin_provider_plugins_are_discoverable():
    """Built-in providers should be plugin descriptors with capability metadata."""
    from par_tts.providers.registry import get_provider_plugins

    plugins = get_provider_plugins(refresh=True, include_entry_points=False)

    assert set(plugins) == {"elevenlabs", "openai", "kokoro-onnx", "deepgram", "gemini"}
    assert plugins["openai"].capabilities.formats == ["mp3", "opus", "aac", "flac", "wav"]
    assert plugins["openai"].capabilities.supports_speed is True
    assert plugins["elevenlabs"].capabilities.supports_voice_controls is True
    assert plugins["deepgram"].capabilities.supports_streaming is True
    assert plugins["kokoro-onnx"].requires_api_key is False


def test_providers_mapping_is_derived_from_plugins():
    """PROVIDERS should remain a provider-class compatibility mapping."""
    from par_tts.providers import PROVIDERS
    from par_tts.providers.openai import OpenAIProvider

    assert PROVIDERS["openai"] is OpenAIProvider
    assert set(PROVIDERS) == {"elevenlabs", "openai", "kokoro-onnx", "deepgram", "gemini"}


def test_entry_point_provider_plugin_loads(monkeypatch):
    """Entry point objects returning ProviderPlugin should be registered."""
    from par_tts.providers.registry import ProviderCapabilities, ProviderPlugin, get_provider_plugins, metadata

    plugin = ProviderPlugin(
        name="external",
        provider_class=MinimalProvider,
        description="External provider",
        capabilities=ProviderCapabilities(formats=["mp3"]),
        default_model="external-model",
        requires_api_key=False,
        source="test",
    )
    monkeypatch.setattr(metadata, "entry_points", lambda group=None: [FakeEntryPoint("external", plugin)] if group else [])

    plugins = get_provider_plugins(refresh=True)

    assert plugins["external"].provider_class is MinimalProvider
    assert plugins["external"].source == "test"


def test_entry_point_provider_class_loads(monkeypatch):
    """Entry point provider classes should be normalized to ProviderPlugin."""
    from par_tts.providers.registry import get_provider_plugins, metadata

    monkeypatch.setattr(metadata, "entry_points", lambda group=None: [FakeEntryPoint("minimal", MinimalProvider)] if group else [])

    plugins = get_provider_plugins(refresh=True)

    assert plugins["minimal"].provider_class is MinimalProvider
    assert plugins["minimal"].description == "Minimal provider"
    assert plugins["minimal"].capabilities.supports_speed is True
    assert plugins["minimal"].default_model == "minimal-model"


def test_broken_entry_point_is_ignored_with_diagnostic(monkeypatch):
    """Bad plugins should not block built-ins and should expose diagnostics."""
    from par_tts.providers.registry import get_plugin_diagnostics, get_provider_plugins, metadata

    monkeypatch.setattr(metadata, "entry_points", lambda group=None: [FakeEntryPoint("broken", error=RuntimeError("boom"))] if group else [])

    plugins = get_provider_plugins(refresh=True)
    diagnostics = get_plugin_diagnostics()

    assert "openai" in plugins
    assert "broken" not in plugins
    assert any("broken" in diagnostic and "boom" in diagnostic for diagnostic in diagnostics)
