"""OpenAI TTS provider implementation."""

import tempfile
from pathlib import Path
from typing import Any, Literal

from openai import OpenAI
from rich.console import Console

from src.providers.base import TTSProvider, Voice

console = Console()


class OpenAIProvider(TTSProvider):
    """OpenAI TTS provider."""

    # Available voices for OpenAI TTS
    VOICES = {
        "alloy": "Alloy - Neutral and balanced",
        "echo": "Echo - Smooth and articulate",
        "fable": "Fable - Expressive and animated",
        "onyx": "Onyx - Deep and authoritative",
        "nova": "Nova - Warm and friendly",
        "shimmer": "Shimmer - Soft and gentle",
    }

    def __init__(self, api_key: str, **kwargs: Any):
        """
        Initialize OpenAI provider.

        Args:
            api_key: OpenAI API key.
            **kwargs: Additional configuration.
        """
        super().__init__(api_key, **kwargs)
        self.client = OpenAI(api_key=api_key, timeout=kwargs.get("timeout", 10.0))

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
        return "tts-1"

    @property
    def default_voice(self) -> str:
        """Default voice for this provider."""
        return "nova"

    def generate_speech(
        self,
        text: str,
        voice: str,
        model: str | None = None,
        response_format: Literal["mp3", "opus", "aac", "flac", "wav", "pcm"] = "mp3",
        speed: float = 1.0,
        **kwargs: Any,
    ) -> bytes:
        """
        Generate speech from text using OpenAI.

        Args:
            text: Text to convert to speech.
            voice: Voice to use (alloy, echo, fable, onyx, nova, shimmer).
            model: Model to use (tts-1 or tts-1-hd).
            response_format: Audio format (mp3, opus, aac, flac, wav).
            speed: Speed of speech (0.25 to 4.0).
            **kwargs: Additional parameters.

        Returns:
            Audio data as bytes.
        """
        if model is None:
            model = self.default_model

        # Ensure speed is within valid range
        speed = max(0.25, min(4.0, speed))

        response = self.client.audio.speech.create(
            model=model,
            voice=voice,  # type: ignore
            input=text,
            response_format=response_format,  # type: ignore
            speed=speed,
        )

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
                console.print(f"[green]✓ Resolved '{voice_identifier}' to voice: {voice_id}[/green]")
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

    def play_audio(self, audio_data: bytes) -> None:
        """
        Play audio data.

        Args:
            audio_data: Audio data to play.
        """
        # OpenAI doesn't provide a play function, so we'll use a temporary file
        # and system audio player
        import subprocess
        import sys

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
            tmp.write(audio_data)
            tmp_path = tmp.name

        try:
            # Determine the appropriate command based on the platform
            if sys.platform == "darwin":  # macOS
                subprocess.run(["afplay", tmp_path], check=True)
            elif sys.platform == "win32":  # Windows
                subprocess.run(["start", "", tmp_path], shell=True, check=True)
            else:  # Linux and others
                # Try common audio players
                for player in ["aplay", "paplay", "ffplay", "mpg123"]:
                    try:
                        subprocess.run([player, tmp_path], check=True)
                        break
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue
                else:
                    console.print("[yellow]Warning: Could not find audio player. Audio saved but not played.[/yellow]")
        finally:
            # Clean up temp file
            Path(tmp_path).unlink(missing_ok=True)
