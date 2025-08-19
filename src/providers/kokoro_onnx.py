"""Kokoro ONNX TTS provider."""

import os
import tempfile
from pathlib import Path

import soundfile as sf
from kokoro_onnx import Kokoro

from src.model_downloader import ModelDownloader

from .base import TTSProvider, Voice


class KokoroONNXProvider(TTSProvider):
    """Kokoro ONNX TTS provider implementation."""

    def __init__(self, model_path: str | None = None, voice_path: str | None = None):
        """Initialize Kokoro ONNX provider.

        Args:
            model_path: Path to ONNX model file (kokoro-v1.0.onnx).
                       If not provided, will check KOKORO_MODEL_PATH env var,
                       then auto-download to XDG data directory if needed.
            voice_path: Path to voice file (voices-v1.0.bin).
                       If not provided, will check KOKORO_VOICE_PATH env var,
                       then auto-download to XDG data directory if needed.
        """
        # Check for explicitly provided paths or environment variables
        env_model_path = os.environ.get("KOKORO_MODEL_PATH")
        env_voice_path = os.environ.get("KOKORO_VOICE_PATH")

        if model_path or env_model_path:
            # Use provided paths
            self.model_path = model_path or env_model_path or ""
            self.voice_path = voice_path or env_voice_path or "voices-v1.0.bin"

            # Check if files exist
            if not self.model_path or not Path(self.model_path).exists():
                raise FileNotFoundError(
                    f"Model file not found: {self.model_path}. "
                    "Remove KOKORO_MODEL_PATH to auto-download or provide a valid path."
                )
            if not Path(self.voice_path).exists():
                raise FileNotFoundError(
                    f"Voice file not found: {self.voice_path}. "
                    "Remove KOKORO_VOICE_PATH to auto-download or provide a valid path."
                )
        else:
            # Auto-download models if needed
            downloader = ModelDownloader()
            model_path_obj, voice_path_obj = downloader.download_models()
            self.model_path = str(model_path_obj)
            self.voice_path = str(voice_path_obj)

        # Initialize Kokoro
        self.kokoro = Kokoro(self.model_path, self.voice_path)
        self._voices: list[str] | None = None

    @property
    def name(self) -> str:
        """Provider name."""
        return "kokoro-onnx"

    @property
    def supported_formats(self) -> list[str]:
        """Supported audio formats."""
        return ["wav", "flac", "ogg"]

    @property
    def default_model(self) -> str:
        """Default model name."""
        return "kokoro-v1.0"

    @property
    def default_voice(self) -> str:
        """Default voice ID."""
        return "af_sarah"

    def list_voices(self) -> list[Voice]:
        """List available voices.

        Returns:
            List of Voice objects.
        """
        if self._voices is None:
            self._voices = self.kokoro.get_voices()

        # Return as Voice objects
        return [Voice(id=voice, name=voice) for voice in self._voices]

    def resolve_voice(self, voice_name: str) -> str:
        """Resolve voice name to voice ID.

        Args:
            voice_name: Voice name or ID to resolve.

        Returns:
            Resolved voice ID.
        """
        available_voices = self.kokoro.get_voices()

        # Check if it's already a valid voice ID
        if voice_name in available_voices:
            return voice_name

        # Try case-insensitive match
        voice_lower = voice_name.lower()
        for voice in available_voices:
            if voice.lower() == voice_lower:
                return voice

        # Try partial match
        matches = [v for v in available_voices if voice_lower in v.lower()]
        if len(matches) == 1:
            return matches[0]
        elif len(matches) > 1:
            raise ValueError(f"Ambiguous voice name '{voice_name}'. Matches: {', '.join(matches)}")

        # No match found
        raise ValueError(f"Voice '{voice_name}' not found. Available voices: {', '.join(available_voices)}")

    def generate_speech(
        self, text: str, voice: str, model: str | None = None, output_format: str = "wav", **kwargs
    ) -> bytes:
        """Generate speech from text.

        Args:
            text: Text to convert to speech.
            voice: Voice ID to use.
            model: Model to use (ignored, uses loaded model).
            output_format: Output audio format.
            **kwargs: Additional provider-specific options:
                - speed: Speech speed (default: 1.0).
                - lang: Language code (default: "en-us").

        Returns:
            Audio data as bytes.
        """
        # Extract provider-specific options
        speed = kwargs.get("speed", 1.0)
        lang = kwargs.get("lang", "en-us")

        # Generate audio
        samples, sample_rate = self.kokoro.create(text, voice=voice, speed=speed, lang=lang)

        # Convert to requested format
        with tempfile.NamedTemporaryFile(suffix=f".{output_format}", delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Save audio to temp file
            sf.write(temp_path, samples, sample_rate)

            # Read back as bytes
            with open(temp_path, "rb") as f:
                audio_data = f.read()

            return audio_data
        finally:
            # Clean up temp file
            if Path(temp_path).exists():
                Path(temp_path).unlink()

    def save_audio(self, audio_data: bytes, file_path: str, format: str | None = None) -> None:
        """Save audio data to file.

        Args:
            audio_data: Audio data as bytes.
            file_path: Path to save the audio file.
            format: Audio format (inferred from file extension if not provided).
        """
        # For Kokoro, audio_data is already in the correct format
        # Just write it directly
        with open(file_path, "wb") as f:
            f.write(audio_data)

    def play_audio(self, audio_data: bytes) -> None:
        """Play audio data.

        Args:
            audio_data: Audio data as bytes.
        """
        # Save to temp file and play
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
            temp_file.write(audio_data)
            temp_path = temp_file.name

        try:
            # Use system command to play audio
            import platform
            import subprocess

            system = platform.system()
            if system == "Darwin":  # macOS
                subprocess.run(["afplay", temp_path], check=True)
            elif system == "Windows":
                subprocess.run(["start", "", temp_path], shell=True, check=True)
            else:  # Linux and others
                # Try different players in order of preference
                players = ["aplay", "paplay", "ffplay", "mpg123"]
                for player in players:
                    try:
                        subprocess.run([player, temp_path], check=True)
                        break
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        continue
                else:
                    raise RuntimeError("No audio player found. Install aplay, paplay, ffplay, or mpg123.")
        finally:
            # Clean up temp file
            if Path(temp_path).exists():
                Path(temp_path).unlink()
