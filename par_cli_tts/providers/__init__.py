"""TTS Provider implementations."""

from par_cli_tts.providers.base import TTSProvider, Voice
from par_cli_tts.providers.deepgram import DeepgramProvider
from par_cli_tts.providers.elevenlabs import ElevenLabsProvider
from par_cli_tts.providers.gemini import GeminiProvider
from par_cli_tts.providers.kokoro_onnx import KokoroONNXProvider
from par_cli_tts.providers.openai import OpenAIProvider

__all__ = [
    "TTSProvider",
    "Voice",
    "DeepgramProvider",
    "ElevenLabsProvider",
    "GeminiProvider",
    "OpenAIProvider",
    "KokoroONNXProvider",
]

PROVIDERS = {
    "elevenlabs": ElevenLabsProvider,
    "openai": OpenAIProvider,
    "kokoro-onnx": KokoroONNXProvider,
    "deepgram": DeepgramProvider,
    "gemini": GeminiProvider,
}
