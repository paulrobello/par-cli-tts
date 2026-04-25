"""Tests for configuration modules."""

from pathlib import Path

import pytest

from par_tts.cli.config import AudioSettings, OutputSettings, ProviderSettings, TTSConfig
from par_tts.cli.config_file import ConfigFile, ConfigManager


class TestAudioSettings:
    """Tests for AudioSettings dataclass."""

    def test_default_values(self):
        """Should have correct default values."""
        settings = AudioSettings()
        assert settings.format == "mp3"
        assert settings.speed == 1.0
        assert settings.stability == 0.5
        assert settings.similarity_boost == 0.5
        assert settings.response_format == "mp3"
        assert settings.lang == "en-us"

    def test_custom_values(self):
        """Should accept custom values."""
        settings = AudioSettings(format="wav", speed=1.5, stability=0.8)
        assert settings.format == "wav"
        assert settings.speed == 1.5
        assert settings.stability == 0.8


class TestOutputSettings:
    """Tests for OutputSettings dataclass."""

    def test_default_values(self):
        """Should have correct default values."""
        settings = OutputSettings()
        assert settings.output_path is None
        assert settings.play_audio is True
        assert settings.keep_temp is False
        assert settings.temp_dir is None
        assert settings.debug is False

    def test_custom_values(self):
        """Should accept custom values."""
        settings = OutputSettings(
            output_path=Path("/tmp/audio.mp3"),
            play_audio=False,
            keep_temp=True,
        )
        assert settings.output_path == Path("/tmp/audio.mp3")
        assert settings.play_audio is False
        assert settings.keep_temp is True


class TestProviderSettings:
    """Tests for ProviderSettings dataclass."""

    def test_default_values(self):
        """Should have correct default values."""
        settings = ProviderSettings()
        assert settings.provider == "kokoro-onnx"
        assert settings.voice is None
        assert settings.model is None
        assert settings.api_key is None

    def test_custom_values(self):
        """Should accept custom values."""
        settings = ProviderSettings(
            provider="elevenlabs",
            voice="Rachel",
            model="eleven_monolingual_v1",
        )
        assert settings.provider == "elevenlabs"
        assert settings.voice == "Rachel"


class TestTTSConfig:
    """Tests for TTSConfig dataclass."""

    def test_get_provider_kwargs_elevenlabs(self):
        """Should return correct kwargs for ElevenLabs."""
        config = TTSConfig(
            text="Hello",
            provider_settings=ProviderSettings(provider="elevenlabs"),
            audio_settings=AudioSettings(stability=0.7, similarity_boost=0.8),
            output_settings=OutputSettings(),
        )

        kwargs = config.get_provider_kwargs()
        assert kwargs["stability"] == 0.7
        assert kwargs["similarity_boost"] == 0.8

    def test_get_provider_kwargs_openai(self):
        """Should return correct kwargs for OpenAI."""
        config = TTSConfig(
            text="Hello",
            provider_settings=ProviderSettings(provider="openai"),
            audio_settings=AudioSettings(speed=1.5, response_format="wav"),
            output_settings=OutputSettings(),
        )

        kwargs = config.get_provider_kwargs()
        assert kwargs["speed"] == 1.5
        assert kwargs["response_format"] == "wav"

    def test_get_provider_kwargs_kokoro(self):
        """Should return correct kwargs for Kokoro ONNX."""
        config = TTSConfig(
            text="Hello",
            provider_settings=ProviderSettings(provider="kokoro-onnx"),
            audio_settings=AudioSettings(speed=1.2, lang="en-gb", format="wav"),
            output_settings=OutputSettings(),
        )

        kwargs = config.get_provider_kwargs()
        assert kwargs["speed"] == 1.2
        assert kwargs["lang"] == "en-gb"
        assert kwargs["output_format"] == "wav"


class TestConfigFile:
    """Tests for ConfigFile Pydantic model."""

    def test_default_values(self):
        """Should have None defaults for optional fields."""
        config = ConfigFile()
        assert config.provider is None
        assert config.voice is None
        assert config.model is None

    def test_custom_values(self):
        """Should accept valid custom values."""
        config = ConfigFile(
            provider="elevenlabs",
            voice="Rachel",
            volume=1.5,
            speed=1.2,
        )
        assert config.provider == "elevenlabs"
        assert config.voice == "Rachel"
        assert config.volume == 1.5
        assert config.speed == 1.2

    def test_volume_validation(self):
        """Should validate volume range."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ConfigFile(volume=6.0)  # Over max of 5.0

        with pytest.raises(Exception):  # Pydantic ValidationError
            ConfigFile(volume=-0.1)  # Under min of 0.0

    def test_speed_validation(self):
        """Should validate speed range."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ConfigFile(speed=5.0)  # Over max of 4.0

        with pytest.raises(Exception):  # Pydantic ValidationError
            ConfigFile(speed=0.1)  # Under min of 0.25

    def test_voices_per_provider(self):
        """Should accept a per-provider voices mapping for known providers."""
        config = ConfigFile(
            voices={
                "elevenlabs": "Rachel",
                "openai": "nova",
                "kokoro-onnx": "af_sarah",
            }
        )
        assert config.voices is not None
        assert config.voices["elevenlabs"] == "Rachel"
        assert config.voices["openai"] == "nova"
        assert config.voices["kokoro-onnx"] == "af_sarah"

    def test_voices_rejects_unknown_provider(self):
        """Should reject unknown provider keys in voices mapping."""
        with pytest.raises(Exception):  # Pydantic ValidationError
            ConfigFile(voices={"bogus": "foo"})


class TestConfigManager:
    """Tests for ConfigManager class."""

    def test_load_missing_config(self, tmp_path, monkeypatch):
        """Should return None for missing config file."""
        monkeypatch.setattr(
            "par_tts.cli.config_file.platformdirs.user_config_dir",
            lambda _: str(tmp_path)
        )

        manager = ConfigManager()
        config = manager.load_config()

        assert config is None

    def test_create_sample_config(self, tmp_path, monkeypatch):
        """Should create a sample config file."""
        monkeypatch.setattr(
            "par_tts.cli.config_file.platformdirs.user_config_dir",
            lambda _: str(tmp_path)
        )

        manager = ConfigManager()
        manager.create_sample_config()

        assert manager.config_file.exists()
        content = manager.config_file.read_text()
        assert "# PAR CLI TTS Configuration" in content

    def test_merge_with_cli_args(self, tmp_path, monkeypatch):
        """Should merge config file with CLI args, CLI taking precedence."""
        monkeypatch.setattr(
            "par_tts.cli.config_file.platformdirs.user_config_dir",
            lambda _: str(tmp_path)
        )

        manager = ConfigManager()
        manager.config_data = ConfigFile(provider="elevenlabs", volume=1.5)

        merged = manager.merge_with_cli_args(provider="openai", voice="nova")

        assert merged["provider"] == "openai"  # CLI override
        assert merged["volume"] == 1.5  # From config
        assert merged["voice"] == "nova"  # From CLI

    def test_get_value(self, tmp_path, monkeypatch):
        """Should get config values with defaults."""
        monkeypatch.setattr(
            "par_tts.cli.config_file.platformdirs.user_config_dir",
            lambda _: str(tmp_path)
        )

        manager = ConfigManager()
        manager.config_data = ConfigFile(provider="kokoro-onnx")

        assert manager.get_value("provider") == "kokoro-onnx"
        assert manager.get_value("missing", "default") == "default"
