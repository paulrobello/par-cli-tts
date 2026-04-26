"""Central default values for PAR CLI TTS.

This module provides default configuration values for all providers
to avoid duplication and ensure consistency.
"""

import os

# Default provider
DEFAULT_PROVIDER = "kokoro-onnx"

# Default voices by provider
DEFAULT_ELEVENLABS_VOICE = "Juniper"
DEFAULT_OPENAI_VOICE = "nova"
DEFAULT_KOKORO_VOICE = "af_sarah"
DEFAULT_DEEPGRAM_VOICE = "aura-2-thalia-en"
DEFAULT_GEMINI_VOICE = "Kore"

DEFAULT_MODELS: dict[str, str] = {
    "elevenlabs": "eleven_multilingual_v2",
    "openai": "gpt-4o-mini-tts",
    "kokoro-onnx": "kokoro-v1.0",
    "deepgram": DEFAULT_DEEPGRAM_VOICE,
    "gemini": "gemini-2.5-flash-preview-tts",
}


def get_default_voice(provider: str) -> str:
    """Get default voice for the specified provider.

    Args:
        provider: Provider name (elevenlabs, openai, kokoro-onnx, deepgram, gemini).

    Returns:
        Default voice ID for the provider, checking environment
        variables first, then falling back to built-in defaults.
    """
    defaults = {
        "elevenlabs": os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_ELEVENLABS_VOICE),
        "openai": os.getenv("OPENAI_VOICE_ID", DEFAULT_OPENAI_VOICE),
        "kokoro-onnx": os.getenv("KOKORO_VOICE_ID", DEFAULT_KOKORO_VOICE),
        "deepgram": os.getenv("DEEPGRAM_VOICE_ID", DEFAULT_DEEPGRAM_VOICE),
        "gemini": os.getenv("GEMINI_VOICE_ID", DEFAULT_GEMINI_VOICE),
    }
    return defaults.get(provider, "")
