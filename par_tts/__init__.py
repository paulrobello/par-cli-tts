"""PAR TTS — Text-to-speech library with multiple provider support.

Usage:
    from par_tts import get_provider, list_providers

    # List available providers
    print(list_providers())

    # Get a provider class
    KokoroTTS = get_provider("kokoro-onnx")
    provider = KokoroTTS()  # no API key needed

    # Generate speech
    audio = provider.generate_speech("Hello world", voice="af_sarah")

    # Save to file
    provider.save_audio(audio, "output.wav")
"""

__version__ = "0.5.0"

from par_tts.audio_processing import AudioProcessingOptions
from par_tts.costs import COST_PER_MILLION_CHARS, CostEstimate, estimate_synthesis_cost
from par_tts.diagnostics import DiagnosticCheck, collect_diagnostics
from par_tts.errors import ErrorType, TTSError
from par_tts.model_downloader import ModelDownloader
from par_tts.pipeline import SpeechPipeline
from par_tts.provider_factory import create_provider
from par_tts.providers import PROVIDERS
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
from par_tts.providers.registry import get_provider_plugin, get_provider_plugins, list_provider_plugins
from par_tts.retry import RetryPolicy
from par_tts.text_processing import TextProcessingOptions, TextSegment, build_text_segments
from par_tts.voice_packs import VoicePack, VoicePackRecommendation, get_voice_pack, load_voice_packs
from par_tts.voice_search import search_voices

__all__ = [
    "__version__",
    "TTSProvider",
    "Voice",
    "AudioData",
    "AsyncAudioData",
    "ProviderCapabilities",
    "ProviderPlugin",
    "SpeechCallbacks",
    "SpeechProgress",
    "SpeechComplete",
    "SpeechPipeline",
    "TextSegment",
    "TextProcessingOptions",
    "AudioProcessingOptions",
    "RetryPolicy",
    "ProviderOptions",
    "ProviderOptionSchema",
    "PROVIDER_OPTION_SCHEMAS",
    "ElevenLabsOptions",
    "OpenAIOptions",
    "KokoroOptions",
    "DeepgramOptions",
    "GeminiOptions",
    "PROVIDERS",
    "TTSError",
    "ErrorType",
    "VoicePack",
    "VoicePackRecommendation",
    "CostEstimate",
    "DiagnosticCheck",
    "ModelDownloader",
    "COST_PER_MILLION_CHARS",
    "get_provider",
    "create_provider",
    "list_providers",
    "get_provider_plugin",
    "get_provider_plugins",
    "list_provider_plugins",
    "get_provider_option_schema",
    "options_to_kwargs",
    "build_text_segments",
    "search_voices",
    "load_voice_packs",
    "get_voice_pack",
    "estimate_synthesis_cost",
    "collect_diagnostics",
]


def get_provider(name: str) -> type[TTSProvider]:
    """Get a provider class by name.

    Args:
        name: Provider identifier (e.g. "elevenlabs", "kokoro-onnx").

    Returns:
        The provider class (not an instance).

    Raises:
        ValueError: If the provider name is not recognized.
    """
    if name not in PROVIDERS:
        raise ValueError(f"Unknown provider '{name}'. Available: {', '.join(sorted(PROVIDERS))}")
    return PROVIDERS[name]


def list_providers() -> list[str]:
    """Return a sorted list of available provider names."""
    return sorted(PROVIDERS.keys())
