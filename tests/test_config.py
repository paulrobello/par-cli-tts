"""Tests for configuration modules."""

import pytest
from pydantic import ValidationError

from par_tts.cli.config_file import ConfigFile, ConfigManager


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
        with pytest.raises(ValidationError):
            ConfigFile(volume=6.0)  # Over max of 5.0

        with pytest.raises(ValidationError):
            ConfigFile(volume=-0.1)  # Under min of 0.0

    def test_speed_validation(self):
        """Should validate speed range."""
        with pytest.raises(ValidationError):
            ConfigFile(speed=5.0)  # Over max of 4.0

        with pytest.raises(ValidationError):
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
        with pytest.raises(ValidationError):
            ConfigFile(voices={"bogus": "foo"})

    def test_profiles_accept_valid_profile_settings(self):
        """Should accept named config profiles with normal config settings."""
        config = ConfigFile(
            provider="kokoro-onnx",
            profiles={
                "podcast": {
                    "provider": "openai",
                    "voice": "nova",
                    "speed": 0.95,
                }
            },
        )

        assert config.profiles is not None
        assert config.profiles["podcast"].provider == "openai"
        assert config.profiles["podcast"].voice == "nova"

    def test_profiles_reject_unknown_settings(self):
        """Should reject unknown fields inside profiles."""
        with pytest.raises(ValidationError):
            ConfigFile(profiles={"bad": {"not_a_setting": True}})

    def test_core_enhancement_settings(self):
        """Should accept core text/audio pipeline settings in base config and profiles."""
        config = ConfigFile(
            chunk=True,
            max_chars=500,
            markup=True,
            voice_sections=True,
            pronunciations={"NASA": "N A S A"},
            auto_lang=True,
            trim_silence=True,
            normalize=True,
            post_process_preset="podcast",
            fade_in_ms=100,
            fade_out_ms=200,
            profiles={"narration": {"chunk": True, "post_process_preset": "notification"}},
        )

        assert config.chunk is True
        assert config.max_chars == 500
        assert config.pronunciations == {"NASA": "N A S A"}
        assert config.profiles is not None
        assert config.profiles["narration"].post_process_preset == "notification"


class TestConfigManager:
    """Tests for ConfigManager class."""

    def test_load_missing_config(self, tmp_path, monkeypatch):
        """Should return None for missing config file."""
        monkeypatch.setattr("par_tts.cli.config_file.platformdirs.user_config_dir", lambda _: str(tmp_path))

        manager = ConfigManager()
        config = manager.load_config()

        assert config is None

    def test_create_sample_config(self, tmp_path, monkeypatch):
        """Should create a sample config file."""
        monkeypatch.setattr("par_tts.cli.config_file.platformdirs.user_config_dir", lambda _: str(tmp_path))

        manager = ConfigManager()
        manager.create_sample_config()

        assert manager.config_file.exists()
        content = manager.config_file.read_text()
        assert "# PAR CLI TTS Configuration" in content

    def test_merge_with_cli_args(self, tmp_path, monkeypatch):
        """Should merge config file with CLI args, CLI taking precedence."""
        monkeypatch.setattr("par_tts.cli.config_file.platformdirs.user_config_dir", lambda _: str(tmp_path))

        manager = ConfigManager()
        manager.config_data = ConfigFile(provider="elevenlabs", volume=1.5)

        merged = manager.merge_with_cli_args(provider="openai", voice="nova")

        assert merged["provider"] == "openai"  # CLI override
        assert merged["volume"] == 1.5  # From config
        assert merged["voice"] == "nova"  # From CLI

    def test_get_value(self, tmp_path, monkeypatch):
        """Should get config values with defaults."""
        monkeypatch.setattr("par_tts.cli.config_file.platformdirs.user_config_dir", lambda _: str(tmp_path))

        manager = ConfigManager()
        manager.config_data = ConfigFile(provider="kokoro-onnx")

        assert manager.get_value("provider") == "kokoro-onnx"
        assert manager.get_value("missing", "default") == "default"

    def test_apply_profile_overrides_base_config(self, tmp_path, monkeypatch):
        """Selected profile values should override base config values."""
        monkeypatch.setattr("par_tts.cli.config_file.platformdirs.user_config_dir", lambda _: str(tmp_path))

        manager = ConfigManager()
        config = ConfigFile(
            provider="kokoro-onnx",
            voice="af_sarah",
            volume=1.0,
            profiles={
                "podcast": {
                    "provider": "openai",
                    "voice": "nova",
                    "speed": 0.95,
                }
            },
        )

        profiled = manager.apply_profile(config, "podcast")

        assert profiled.provider == "openai"
        assert profiled.voice == "nova"
        assert profiled.speed == 0.95
        assert profiled.volume == 1.0

    def test_apply_profile_rejects_unknown_profile(self, tmp_path, monkeypatch):
        """Unknown profile names should fail clearly."""
        monkeypatch.setattr("par_tts.cli.config_file.platformdirs.user_config_dir", lambda _: str(tmp_path))

        manager = ConfigManager()
        config = ConfigFile(provider="kokoro-onnx", profiles={"podcast": {"provider": "openai"}})

        with pytest.raises(ValueError, match="Unknown profile"):
            manager.apply_profile(config, "missing")
