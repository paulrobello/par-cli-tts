"""TTS Provider implementations."""

from par_tts.providers.base import (
    DeepgramOptions,
    ElevenLabsOptions,
    GeminiOptions,
    KokoroOptions,
    OpenAIOptions,
    ProviderCapabilities,
    ProviderPlugin,
    TTSProvider,
    Voice,
)
from par_tts.providers.deepgram import DeepgramProvider
from par_tts.providers.elevenlabs import ElevenLabsProvider
from par_tts.providers.gemini import GeminiProvider
from par_tts.providers.kokoro_onnx import KokoroONNXProvider
from par_tts.providers.openai import OpenAIProvider
from par_tts.providers.registry import (
    get_builtin_provider_plugins,
    get_plugin_diagnostics,
    get_provider_classes,
    get_provider_plugin,
    get_provider_plugins,
    list_provider_plugins,
)

__all__ = [
    "TTSProvider",
    "Voice",
    "ProviderCapabilities",
    "ProviderPlugin",
    "ElevenLabsOptions",
    "OpenAIOptions",
    "KokoroOptions",
    "DeepgramOptions",
    "GeminiOptions",
    "DeepgramProvider",
    "ElevenLabsProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "KokoroONNXProvider",
    "get_builtin_provider_plugins",
    "get_plugin_diagnostics",
    "get_provider_classes",
    "get_provider_plugin",
    "get_provider_plugins",
    "list_provider_plugins",
]

PROVIDERS = get_provider_classes()
