"""ElevenLabs TTS provider implementation."""

from pathlib import Path
from typing import Any

from elevenlabs import VoiceSettings, play, save
from elevenlabs.client import ElevenLabs
from rich.console import Console

from src.providers.base import TTSProvider, Voice
from src.voice_cache import VoiceCache, resolve_voice_identifier

console = Console()


class ElevenLabsProvider(TTSProvider):
    """ElevenLabs TTS provider."""

    def __init__(self, api_key: str, **kwargs: Any):
        """
        Initialize ElevenLabs provider.

        Args:
            api_key: ElevenLabs API key.
            **kwargs: Additional configuration.
        """
        super().__init__(api_key, **kwargs)
        self.client = ElevenLabs(api_key=api_key, timeout=kwargs.get("timeout", 10.0))
        self.cache = VoiceCache(app_name="par-tts-elevenlabs")

    @property
    def name(self) -> str:
        """Provider name."""
        return "ElevenLabs"

    @property
    def supported_formats(self) -> list[str]:
        """List of supported audio formats."""
        return ["mp3", "pcm", "ulaw"]

    @property
    def default_model(self) -> str:
        """Default model for this provider."""
        return "eleven_monolingual_v1"

    @property
    def default_voice(self) -> str:
        """Default voice for this provider."""
        return "aMSt68OGf4xUZAnLpTU8"

    def generate_speech(
        self,
        text: str,
        voice: str,
        model: str | None = None,
        stability: float = 0.5,
        similarity_boost: float = 0.5,
        **kwargs: Any,
    ) -> bytes:
        """
        Generate speech from text using ElevenLabs.

        Args:
            text: Text to convert to speech.
            voice: Voice ID to use.
            model: Model to use (default: eleven_monolingual_v1).
            stability: Voice stability (0.0 to 1.0).
            similarity_boost: Voice similarity boost (0.0 to 1.0).
            **kwargs: Additional parameters.

        Returns:
            Audio data as bytes.
        """
        if model is None:
            model = self.default_model

        audio = self.client.text_to_speech.convert(
            text=text,
            voice_id=voice,
            model_id=model,
            voice_settings=VoiceSettings(
                stability=stability,
                similarity_boost=similarity_boost,
            ),
        )

        # Convert generator to bytes
        audio_bytes = b"".join(audio)
        return audio_bytes

    def list_voices(self) -> list[Voice]:
        """
        List available voices from ElevenLabs.

        Returns:
            List of available Voice objects.
        """
        voices_response = self.client.voices.get_all()
        voices = []

        for voice_obj in voices_response.voices:
            labels = list(voice_obj.labels.values()) if voice_obj.labels else []
            voices.append(
                Voice(
                    id=voice_obj.voice_id,
                    name=voice_obj.name or "Unknown",
                    labels=labels,
                    category=voice_obj.category if hasattr(voice_obj, "category") else None,
                )
            )

        return voices

    def resolve_voice(self, voice_identifier: str) -> str:
        """
        Resolve a voice name or ID to a valid voice ID.

        Args:
            voice_identifier: Voice name or ID to resolve.

        Returns:
            Valid voice ID for ElevenLabs.

        Raises:
            ValueError: If voice cannot be resolved.
        """
        return resolve_voice_identifier(
            voice_identifier,
            self.client,
            self.cache,
            update_cache_if_needed=True,
        )

    def save_audio(self, audio_data: bytes, file_path: str | Path) -> None:
        """
        Save audio data to a file.

        Args:
            audio_data: Audio data to save.
            file_path: Path to save the audio file.
        """
        save(audio_data, str(file_path))

    def play_audio(self, audio_data: bytes) -> None:
        """
        Play audio data.

        Args:
            audio_data: Audio data to play.
        """
        play(audio_data)
