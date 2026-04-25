"""Configuration dataclasses for PAR CLI TTS."""

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class AudioSettings:
    """Audio-related settings for TTS generation."""

    format: str = "mp3"
    speed: float = 1.0
    stability: float = 0.5
    similarity_boost: float = 0.5
    response_format: str = "mp3"
    lang: str = "en-us"


@dataclass
class OutputSettings:
    """Output and file management settings."""

    output_path: Path | None = None
    play_audio: bool = True
    keep_temp: bool = False
    temp_dir: Path | None = None
    debug: bool = False


@dataclass
class ProviderSettings:
    """Provider-specific settings."""

    provider: str = "kokoro-onnx"
    voice: str | None = None
    model: str | None = None
    api_key: str | None = None


@dataclass
class TTSConfig:
    """Complete TTS configuration."""

    text: str
    provider_settings: ProviderSettings
    audio_settings: AudioSettings
    output_settings: OutputSettings

    def get_provider_kwargs(self) -> dict[str, Any]:
        """Get provider-specific keyword arguments."""
        kwargs = {}

        # Add audio settings based on provider
        if self.provider_settings.provider == "elevenlabs":
            kwargs["stability"] = self.audio_settings.stability
            kwargs["similarity_boost"] = self.audio_settings.similarity_boost
        elif self.provider_settings.provider == "openai":
            kwargs["speed"] = self.audio_settings.speed
            kwargs["response_format"] = self.audio_settings.response_format
        elif self.provider_settings.provider == "kokoro-onnx":
            kwargs["speed"] = self.audio_settings.speed
            kwargs["lang"] = self.audio_settings.lang
            kwargs["output_format"] = self.audio_settings.format

        return kwargs
