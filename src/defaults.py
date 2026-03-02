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


def get_default_voice(provider: str) -> str:
    """Get default voice for the specified provider.

    Args:
        provider: Provider name (elevenlabs, openai, kokoro-onnx).

    Returns:
        Default voice ID for the provider, checking environment
        variables first, then falling back to built-in defaults.
    """
    defaults = {
        "elevenlabs": os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_ELEVENLABS_VOICE),
        "openai": os.getenv("OPENAI_VOICE_ID", DEFAULT_OPENAI_VOICE),
        "kokoro-onnx": os.getenv("KOKORO_VOICE_ID", DEFAULT_KOKORO_VOICE),
    }
    return defaults.get(provider, "")
