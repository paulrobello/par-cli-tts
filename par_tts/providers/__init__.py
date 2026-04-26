"""TTS Provider implementations."""

from par_tts.providers.base import (
    PROVIDER_OPTION_SCHEMAS,
    AsyncAudioData,
    AudioData,
    DeepgramOptions,
    ElevenLabsOptions,
    GeminiOptions,
    KokoroOptions,
    OpenAIOptions,
    ProviderCapabilities,
    ProviderOptions,
    ProviderOptionSchema,
    ProviderPlugin,
    SpeechCallbacks,
    SpeechComplete,
    SpeechProgress,
    TTSProvider,
    Voice,
    get_provider_option_schema,
    options_to_kwargs,
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
    "AudioData",
    "AsyncAudioData",
    "ProviderCapabilities",
    "ProviderPlugin",
    "SpeechCallbacks",
    "SpeechComplete",
    "SpeechProgress",
    "ProviderOptions",
    "ProviderOptionSchema",
    "PROVIDER_OPTION_SCHEMAS",
    "ElevenLabsOptions",
    "OpenAIOptions",
    "KokoroOptions",
    "DeepgramOptions",
    "GeminiOptions",
    "get_provider_option_schema",
    "options_to_kwargs",
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
