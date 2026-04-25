"""OpenAI TTS provider implementation."""

import logging
from collections.abc import Iterator
from pathlib import Path
from typing import Any, Literal

from openai import OpenAI

from par_cli_tts.audio import play_audio_bytes
from par_cli_tts.defaults import DEFAULT_OPENAI_VOICE
from par_cli_tts.http_client import create_http_client
from par_cli_tts.providers.base import TTSProvider, Voice

_logger = logging.getLogger(__name__)


class OpenAIProvider(TTSProvider):
    """OpenAI TTS provider."""

    # Available voices for OpenAI TTS
    # tts-1/tts-1-hd support: alloy, ash, coral, echo, fable, onyx, nova, sage, shimmer
    # gpt-4o-mini-tts adds: ballad, verse, marin, cedar
    VOICES = {
        "alloy": "Alloy - Neutral and balanced",
        "ash": "Ash - Enthusiastic and energetic",
        "ballad": "Ballad - Warm and soulful",
        "coral": "Coral - Friendly and approachable",
        "echo": "Echo - Smooth and articulate",
        "fable": "Fable - Expressive and animated",
        "nova": "Nova - Warm and friendly",
        "onyx": "Onyx - Deep and authoritative",
        "sage": "Sage - Calm and wise",
        "shimmer": "Shimmer - Soft and gentle",
        "verse": "Verse - Clear and melodic",
        "marin": "Marin - Gentle and soothing",
        "cedar": "Cedar - Rich and resonant",
    }

    def __init__(self, api_key: str, **kwargs: Any):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key.
            **kwargs: Additional configuration.
        """
        super().__init__(api_key, **kwargs)
        # Create httpx client with standard configuration
        http_client = create_http_client(timeout=kwargs.get("timeout", 10.0))
        self.client = OpenAI(api_key=api_key, http_client=http_client)

    @property
    def name(self) -> str:
        """Provider name."""
        return "OpenAI"

    @property
    def supported_formats(self) -> list[str]:
        """List of supported audio formats."""
        return ["mp3", "opus", "aac", "flac", "wav"]

    @property
    def default_model(self) -> str:
        """Default model for this provider."""
        return "gpt-4o-mini-tts"

    @property
    def default_voice(self) -> str:
        """Default voice for this provider."""
        return DEFAULT_OPENAI_VOICE

    def generate_speech(
        self,
        text: str,
        voice: str,
        model: str | None = None,
        response_format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] = "mp3",
        speed: float = 1.0,
        instructions: str | None = None,
        **kwargs: Any,
    ) -> bytes:
        """
        Generate speech from text using OpenAI.

        Args:
            text: Text to convert to speech.
            voice: Voice to use (alloy, ash, ballad, coral, echo, fable, nova, onyx, sage, shimmer, verse, marin, cedar).
            model: Model to use (gpt-4o-mini-tts, tts-1, or tts-1-hd).
            response_format: Audio format (mp3, opus, aac, flac, wav).
            speed: Speed of speech (0.25 to 4.0).
            instructions: Instructions for voice style (gpt-4o-mini-tts only).
            **kwargs: Additional parameters.

        Returns:
            Audio data as bytes.
        """
        if model is None:
            model = self.default_model

        # Ensure speed is within valid range
        speed = max(0.25, min(4.0, speed))

        # Build request parameters
        request_params: dict[str, Any] = {
            "model": model,
            "voice": voice,
            "input": text,
            "response_format": response_format,
            "speed": speed,
        }

        # Add instructions parameter for gpt-4o-mini-tts model
        if instructions and model == "gpt-4o-mini-tts":
            request_params["instructions"] = instructions

        response = self.client.audio.speech.create(**request_params)

        # Get audio data as bytes
        audio_bytes = response.content
        return audio_bytes

    def list_voices(self) -> list[Voice]:
        """
        List available voices from OpenAI.

        Returns:
            List of available Voice objects.
        """
        voices = []

        for voice_id, description in self.VOICES.items():
            # Parse description
            parts = description.split(" - ")
            name = parts[0] if parts else voice_id.capitalize()
            labels = [parts[1]] if len(parts) > 1 else []

            voices.append(
                Voice(
                    id=voice_id,
                    name=name,
                    labels=labels,
                    category="OpenAI TTS",
                )
            )

        return voices

    def resolve_voice(self, voice_identifier: str) -> str:
        """
        Resolve a voice name or ID to a valid voice ID.

        Args:
            voice_identifier: Voice name or ID to resolve.

        Returns:
            Valid voice ID for OpenAI.

        Raises:
            ValueError: If voice cannot be resolved.
        """
        voice_lower = voice_identifier.lower()

        # Check if it's already a valid voice ID
        if voice_lower in self.VOICES:
            return voice_lower

        # Try to match by name
        for voice_id, description in self.VOICES.items():
            name = description.split(" - ")[0].lower()
            if voice_lower == name or voice_lower in name:
                _logger.info("Resolved '%s' to voice: %s", voice_identifier, voice_id)
                return voice_id

        # If no match found, show available voices
        available = ", ".join(self.VOICES.keys())
        raise ValueError(f"Voice '{voice_identifier}' not found. Available voices: {available}")

    def save_audio(self, audio_data: bytes, file_path: str | Path) -> None:
        """
        Save audio data to a file.

        Args:
            audio_data: Audio data to save.
            file_path: Path to save the audio file.
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(audio_data)

    def play_audio(self, audio_data: bytes | Iterator[bytes], volume: float = 1.0) -> None:
        """
        Play audio data with volume control.

        Args:
            audio_data: Audio data to play (bytes or iterator).
            volume: Volume level (0.0 = silent, 1.0 = normal, 2.0 = double volume).
        """
        # Convert iterator to bytes if needed
        if not isinstance(audio_data, bytes):
            audio_data = b"".join(audio_data)

        play_audio_bytes(audio_data, volume=volume, suffix=".mp3")
