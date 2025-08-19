"""TTS Provider implementations."""

from src.providers.base import TTSProvider, Voice
from src.providers.elevenlabs import ElevenLabsProvider
from src.providers.kokoro_onnx import KokoroONNXProvider
from src.providers.openai import OpenAIProvider

__all__ = ["TTSProvider", "Voice", "ElevenLabsProvider", "OpenAIProvider", "KokoroONNXProvider"]

PROVIDERS = {
    "elevenlabs": ElevenLabsProvider,
    "openai": OpenAIProvider,
    "kokoro-onnx": KokoroONNXProvider,
}
