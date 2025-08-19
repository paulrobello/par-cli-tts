"""Base class for TTS providers."""

from abc import ABC, abstractmethod
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

    def __init__(self, api_key: str, **kwargs: Any):
        """
        Initialize the TTS provider.

        Args:
            api_key: API key for the provider.
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
    ) -> bytes:
        """
        Generate speech from text.

        Args:
            text: Text to convert to speech.
            voice: Voice ID or name to use.
            model: Optional model to use (provider-specific).
            **kwargs: Additional provider-specific parameters.

        Returns:
            Audio data as bytes.
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
    def save_audio(self, audio_data: bytes, file_path: str | Path) -> None:
        """
        Save audio data to a file.

        Args:
            audio_data: Audio data to save.
            file_path: Path to save the audio file.
        """
        pass

    @abstractmethod
    def play_audio(self, audio_data: bytes) -> None:
        """
        Play audio data.

        Args:
            audio_data: Audio data to play.
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
