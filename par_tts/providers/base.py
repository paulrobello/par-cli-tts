"""Base class for TTS providers."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class Voice:
    """Represents a TTS voice."""

    id: str
    name: str
    labels: list[str] | None = None
    category: str | None = None


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""

    def __init__(self, api_key: str | None = None, **kwargs: Any):
        """
        Initialize the TTS provider.

        Args:
            api_key: Optional API key for the provider. Some providers (like offline ones) don't need it.
            **kwargs: Additional provider-specific configuration.
        """
        self.api_key = api_key
        self.config = kwargs

    @abstractmethod
    def generate_speech(
        self,
        text: str,
        voice: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> bytes | Iterator[bytes]:
        """
        Generate speech from text.

        Args:
            text: Text to convert to speech.
            voice: Voice ID or name to use.
            model: Optional model to use (provider-specific).
            **kwargs: Additional provider-specific parameters.

        Returns:
            Audio data as bytes or an iterator of bytes for streaming.
        """
        pass

    @abstractmethod
    def list_voices(self) -> list[Voice]:
        """
        List available voices.

        Returns:
            List of available Voice objects.
        """
        pass

    @abstractmethod
    def resolve_voice(self, voice_identifier: str) -> str:
        """
        Resolve a voice name or ID to a valid voice ID.

        Args:
            voice_identifier: Voice name or ID to resolve.

        Returns:
            Valid voice ID for the provider.

        Raises:
            ValueError: If voice cannot be resolved.
        """
        pass

    @abstractmethod
    def save_audio(self, audio_data: bytes | Iterator[bytes], file_path: str | Path) -> None:
        """
        Save audio data to a file.

        Args:
            audio_data: Audio data to save (bytes or iterator for streaming).
            file_path: Path to save the audio file.
        """
        pass

    def stream_to_file(self, audio_stream: Iterator[bytes], file_path: str | Path) -> None:
        """
        Stream audio data directly to file without buffering in memory.

        Args:
            audio_stream: Iterator yielding audio data chunks.
            file_path: Path to save the audio file.
        """
        from par_tts.utils import stream_to_file

        stream_to_file(audio_stream, file_path)

    @abstractmethod
    def play_audio(self, audio_data: bytes | Iterator[bytes], volume: float = 1.0) -> None:
        """
        Play audio data.

        Args:
            audio_data: Audio data to play (bytes or iterator).
            volume: Volume level (0.0 = silent, 1.0 = normal, 2.0 = double volume).
        """
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @property
    @abstractmethod
    def supported_formats(self) -> list[str]:
        """List of supported audio formats."""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model for this provider."""
        pass

    @property
    @abstractmethod
    def default_voice(self) -> str:
        """Default voice for this provider."""
        pass


@dataclass
class SpeechResult:
    """Structured result from speech generation."""

    audio: bytes | Iterator[bytes]
    content_type: str = "audio/mp3"
    sample_rate: int | None = None
    format: str | None = None


@dataclass
class ElevenLabsOptions:
    """ElevenLabs-specific generation options."""

    stability: float = 0.5
    similarity_boost: float = 0.5


@dataclass
class OpenAIOptions:
    """OpenAI-specific generation options."""

    speed: float = 1.0
    response_format: str = "mp3"
    instructions: str | None = None


@dataclass
class KokoroOptions:
    """Kokoro ONNX-specific generation options."""

    speed: float = 1.0
    lang: str = "en-us"
    output_format: str = "wav"


@dataclass
class DeepgramOptions:
    """Deepgram-specific generation options."""

    response_format: str = "mp3"
    sample_rate: int | None = None


@dataclass
class GeminiOptions:
    """Gemini-specific generation options."""
