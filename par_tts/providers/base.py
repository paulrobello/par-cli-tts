"""Base class for TTS providers."""

from abc import ABC, abstractmethod
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from par_tts.retry import RetryPolicy


@dataclass
class Voice:
    """Represents a TTS voice.

    Attributes:
        id: Provider-specific voice identifier (e.g. ``"aura-2-thalia-en"``).
        name: Human-readable voice name (e.g. ``"Thalia"``).
        labels: Optional tags describing voice traits (language, accent, style).
        category: Optional grouping label (e.g. ``"Deepgram Aura-2 (en)"``).
    """

    id: str
    name: str
    labels: list[str] | None = None
    category: str | None = None


@dataclass(frozen=True)
class ProviderCapabilities:
    """Static provider capability metadata used without instantiation."""

    formats: list[str]
    supports_speed: bool = False
    supports_streaming: bool = False
    supports_voice_controls: bool = False
    supports_instructions: bool = False
    supports_sample_rate: bool = False


@dataclass(frozen=True)
class ProviderPlugin:
    """Provider plugin descriptor.

    Descriptors are intentionally static so commands like ``--capabilities`` can
    inspect providers without requiring API keys or creating network clients.
    """

    name: str
    provider_class: type["TTSProvider"]
    description: str
    capabilities: ProviderCapabilities
    default_model: str
    default_voice: str | None = None
    requires_api_key: bool = True
    api_key_env_vars: tuple[str, ...] = ()
    source: str = "builtin"
    cost_per_million_chars: float | None = None


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""

    # Subclasses override this to declare which kwargs they accept for
    # ``generate_speech()``.  Keys are kwarg names; values are defaults.
    # The CLI uses this mapping to build provider-specific option dicts
    # without if/elif chains.
    PROVIDER_KWARGS: dict[str, Any] = {}

    def __init__(self, api_key: str | None = None, **kwargs: Any):
        """
        Initialize the TTS provider.

        Args:
            api_key: Optional API key for the provider. Some providers (like offline ones) don't need it.
            **kwargs: Additional provider-specific configuration.
        """
        self.api_key = api_key
        self.retry_policy = RetryPolicy(
            retry_attempts=int(kwargs.get("retry_attempts", 0)),
            backoff_seconds=float(kwargs.get("retry_backoff", 0.0)),
        )

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

    def save_audio(self, audio_data: bytes | Iterator[bytes], file_path: str | Path) -> None:
        """Save audio data to a file.

        Handles both bytes and iterator inputs.  Providers that need
        special handling (e.g. ElevenLabs SDK ``save``) can override.

        Args:
            audio_data: Audio data to save (bytes or iterator for streaming).
            file_path: Path to save the audio file.
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(audio_data, bytes):
            path.write_bytes(audio_data)
        else:
            self.stream_to_file(audio_data, path)

    def stream_to_file(self, audio_stream: Iterator[bytes], file_path: str | Path) -> None:
        """
        Stream audio data directly to file without buffering in memory.

        Args:
            audio_stream: Iterator yielding audio data chunks.
            file_path: Path to save the audio file.
        """
        from par_tts.utils import stream_to_file

        stream_to_file(audio_stream, file_path)

    def play_audio(self, audio_data: bytes | Iterator[bytes], volume: float = 1.0) -> None:
        """Play audio data with volume control.

        Converts iterator to bytes if needed, then plays via the system
        audio player.  Providers can override for custom playback.

        Args:
            audio_data: Audio data to play (bytes or iterator).
            volume: Volume level (0.0 = silent, 1.0 = normal, 2.0 = double volume).
        """
        from par_tts.audio import play_audio_bytes

        if not isinstance(audio_data, bytes):
            audio_data = b"".join(audio_data)

        # Determine file suffix from supported formats (first entry is default).
        suffix = f".{self.supported_formats[0]}" if self.supported_formats else ".mp3"
        play_audio_bytes(audio_data, volume=volume, suffix=suffix)

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
    """Gemini-specific generation options.

    The Gemini TTS preview API currently offers no tunable generation
    parameters beyond voice and model selection.  This dataclass is
    reserved for future options (e.g. speaking_rate when the API adds it).
    """

    pass
