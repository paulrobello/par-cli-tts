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

from par_tts.providers import PROVIDERS
from par_tts.providers.base import (
    DeepgramOptions,
    ElevenLabsOptions,
    GeminiOptions,
    KokoroOptions,
    OpenAIOptions,
    TTSProvider,
    Voice,
)

__all__ = [
    "__version__",
    "TTSProvider",
    "Voice",
    "ElevenLabsOptions",
    "OpenAIOptions",
    "KokoroOptions",
    "DeepgramOptions",
    "GeminiOptions",
    "PROVIDERS",
    "get_provider",
    "list_providers",
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
