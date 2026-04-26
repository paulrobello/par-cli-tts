"""Provider plugin registry and discovery."""

from __future__ import annotations

import inspect
from importlib import metadata
from typing import Any

from par_tts.defaults import (
    DEFAULT_DEEPGRAM_VOICE,
    DEFAULT_ELEVENLABS_VOICE,
    DEFAULT_GEMINI_VOICE,
    DEFAULT_KOKORO_VOICE,
    DEFAULT_OPENAI_VOICE,
)
from par_tts.providers.base import ProviderCapabilities, ProviderPlugin, TTSProvider
from par_tts.providers.deepgram import DeepgramProvider
from par_tts.providers.elevenlabs import ElevenLabsProvider
from par_tts.providers.gemini import GeminiProvider
from par_tts.providers.kokoro_onnx import KokoroONNXProvider
from par_tts.providers.openai import OpenAIProvider

ENTRY_POINT_GROUP = "par_tts.providers"

_builtin_plugins: tuple[ProviderPlugin, ...] = (
    ProviderPlugin(
        name="elevenlabs",
        provider_class=ElevenLabsProvider,
        description="ElevenLabs",
        capabilities=ProviderCapabilities(
            formats=["mp3", "pcm", "ulaw"],
            supports_streaming=True,
            supports_voice_controls=True,
        ),
        default_model="eleven_multilingual_v2",
        default_voice=DEFAULT_ELEVENLABS_VOICE,
        api_key_env_vars=("ELEVENLABS_API_KEY",),
        cost_per_million_chars=30.0,
    ),
    ProviderPlugin(
        name="openai",
        provider_class=OpenAIProvider,
        description="OpenAI",
        capabilities=ProviderCapabilities(
            formats=["mp3", "opus", "aac", "flac", "wav"],
            supports_speed=True,
            supports_instructions=True,
        ),
        default_model="gpt-4o-mini-tts",
        default_voice=DEFAULT_OPENAI_VOICE,
        api_key_env_vars=("OPENAI_API_KEY",),
        cost_per_million_chars=15.0,
    ),
    ProviderPlugin(
        name="kokoro-onnx",
        provider_class=KokoroONNXProvider,
        description="Kokoro ONNX",
        capabilities=ProviderCapabilities(
            formats=["wav", "flac", "ogg"],
            supports_speed=True,
        ),
        default_model="kokoro-v1.0",
        default_voice=DEFAULT_KOKORO_VOICE,
        requires_api_key=False,
        cost_per_million_chars=0.0,
    ),
    ProviderPlugin(
        name="deepgram",
        provider_class=DeepgramProvider,
        description="Deepgram",
        capabilities=ProviderCapabilities(
            formats=["mp3", "wav", "flac", "opus", "aac"],
            supports_streaming=True,
            supports_sample_rate=True,
        ),
        default_model=DEFAULT_DEEPGRAM_VOICE,
        default_voice=DEFAULT_DEEPGRAM_VOICE,
        api_key_env_vars=("DEEPGRAM_API_KEY", "DG_API_KEY"),
        cost_per_million_chars=30.0,
    ),
    ProviderPlugin(
        name="gemini",
        provider_class=GeminiProvider,
        description="Gemini",
        capabilities=ProviderCapabilities(formats=["wav"]),
        default_model="gemini-2.5-flash-preview-tts",
        default_voice=DEFAULT_GEMINI_VOICE,
        api_key_env_vars=("GEMINI_API_KEY", "GOOGLE_API_KEY"),
        cost_per_million_chars=0.50,
    ),
)

_plugins_cache: dict[str, ProviderPlugin] | None = None
_plugin_diagnostics: list[str] = []


def get_builtin_provider_plugins() -> dict[str, ProviderPlugin]:
    """Return built-in provider plugin descriptors."""
    return {plugin.name: plugin for plugin in _builtin_plugins}


def get_provider_plugins(*, refresh: bool = False, include_entry_points: bool = True) -> dict[str, ProviderPlugin]:
    """Return discovered provider plugins keyed by provider name.

    Args:
        refresh: Rebuild the registry cache.
        include_entry_points: Include third-party entry-point plugins.

    Returns:
        Provider plugin descriptors keyed by name.
    """
    global _plugins_cache

    if refresh or _plugins_cache is None or not include_entry_points:
        plugins = get_builtin_provider_plugins()
        _plugin_diagnostics.clear()
        if include_entry_points:
            plugins.update(_load_entry_point_plugins())
        if include_entry_points:
            _plugins_cache = plugins
        return dict(plugins)

    return dict(_plugins_cache)


def get_provider_classes(*, refresh: bool = False) -> dict[str, type[TTSProvider]]:
    """Return provider classes keyed by provider name."""
    return {name: plugin.provider_class for name, plugin in get_provider_plugins(refresh=refresh).items()}


def get_provider_plugin(name: str) -> ProviderPlugin:
    """Return one provider plugin descriptor by name."""
    plugins = get_provider_plugins()
    if name not in plugins:
        raise ValueError(f"Unknown provider '{name}'. Available: {', '.join(sorted(plugins))}")
    return plugins[name]


def list_provider_plugins() -> list[str]:
    """Return sorted provider plugin names."""
    return sorted(get_provider_plugins())


def get_plugin_diagnostics() -> list[str]:
    """Return diagnostics collected during the latest plugin discovery."""
    return list(_plugin_diagnostics)


def _load_entry_point_plugins() -> dict[str, ProviderPlugin]:
    plugins: dict[str, ProviderPlugin] = {}
    try:
        entry_points = metadata.entry_points(group=ENTRY_POINT_GROUP)
    except TypeError:
        entry_points = metadata.entry_points().select(group=ENTRY_POINT_GROUP)
    except Exception as exc:
        _plugin_diagnostics.append(f"Could not discover provider entry points: {exc}")
        return plugins

    for entry_point in entry_points:
        entry_point_name = getattr(entry_point, "name", "<unknown>")
        try:
            loaded = entry_point.load()
            plugin = _normalize_plugin(entry_point_name, loaded)
            plugins[plugin.name] = plugin
        except Exception as exc:
            _plugin_diagnostics.append(f"Failed to load provider plugin '{entry_point_name}': {exc}")
    return plugins


def _normalize_plugin(entry_point_name: str, loaded: Any) -> ProviderPlugin:
    if isinstance(loaded, ProviderPlugin):
        return loaded

    if inspect.isclass(loaded) and issubclass(loaded, TTSProvider):
        return _provider_class_to_plugin(entry_point_name, loaded)

    if callable(loaded):
        produced = loaded()
        if isinstance(produced, ProviderPlugin):
            return produced
        if inspect.isclass(produced) and issubclass(produced, TTSProvider):
            return _provider_class_to_plugin(entry_point_name, produced)

    raise TypeError("Provider entry point must load a ProviderPlugin, ProviderPlugin factory, or TTSProvider subclass")


def _provider_class_to_plugin(entry_point_name: str, provider_class: type[TTSProvider]) -> ProviderPlugin:
    raw_capabilities = getattr(provider_class, "plugin_capabilities", {})
    capabilities = _coerce_capabilities(raw_capabilities)
    plugin_name = getattr(provider_class, "plugin_name", entry_point_name)
    default_model = getattr(provider_class, "plugin_default_model", "default")
    default_voice = getattr(provider_class, "plugin_default_voice", None)
    requires_api_key = bool(getattr(provider_class, "plugin_requires_api_key", True))
    api_key_env_vars = tuple(getattr(provider_class, "plugin_api_key_env_vars", ()))
    description = getattr(provider_class, "plugin_description", plugin_name)
    cost = getattr(provider_class, "plugin_cost_per_million_chars", None)
    return ProviderPlugin(
        name=plugin_name,
        provider_class=provider_class,
        description=description,
        capabilities=capabilities,
        default_model=default_model,
        default_voice=default_voice,
        requires_api_key=requires_api_key,
        api_key_env_vars=api_key_env_vars,
        source="entry-point",
        cost_per_million_chars=cost,
    )


def _coerce_capabilities(value: ProviderCapabilities | dict[str, Any]) -> ProviderCapabilities:
    if isinstance(value, ProviderCapabilities):
        return value
    if isinstance(value, dict):
        formats = value.get("formats", [])
        return ProviderCapabilities(
            formats=list(formats),
            supports_speed=bool(value.get("supports_speed", False)),
            supports_streaming=bool(value.get("supports_streaming", False)),
            supports_voice_controls=bool(value.get("supports_voice_controls", False)),
            supports_instructions=bool(value.get("supports_instructions", False)),
            supports_sample_rate=bool(value.get("supports_sample_rate", False)),
        )
    raise TypeError("plugin_capabilities must be ProviderCapabilities or dict")
