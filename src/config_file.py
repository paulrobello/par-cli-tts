"""Configuration file support for PAR CLI TTS."""

from pathlib import Path
from typing import Any

import platformdirs
import yaml
from pydantic import BaseModel, Field, ValidationError
from rich.console import Console

console = Console()


class ConfigFile(BaseModel):
    """Configuration file schema."""

    # Provider settings
    provider: str | None = Field(None, description="Default TTS provider")
    voice: str | None = Field(None, description="Default voice")
    model: str | None = Field(None, description="Default model")

    # Output settings
    output_dir: str | None = Field(None, description="Default output directory")
    output_format: str | None = Field(None, description="Default output format")
    keep_temp: bool | None = Field(None, description="Keep temporary files by default")
    temp_dir: str | None = Field(None, description="Default temporary directory")

    # Audio settings
    volume: float | None = Field(None, ge=0.0, le=5.0, description="Default volume")
    speed: float | None = Field(None, ge=0.25, le=4.0, description="Default speed")

    # ElevenLabs specific
    stability: float | None = Field(None, ge=0.0, le=1.0, description="ElevenLabs stability")
    similarity_boost: float | None = Field(None, ge=0.0, le=1.0, description="ElevenLabs similarity")

    # Kokoro specific
    lang: str | None = Field(None, description="Kokoro language code")

    # Behavior settings
    play_audio: bool | None = Field(None, description="Play audio after generation")
    debug: bool | None = Field(None, description="Enable debug output")

    class Config:
        """Pydantic config."""

        extra = "forbid"  # Don't allow unknown fields


class ConfigManager:
    """Manages configuration file loading and merging."""

    def __init__(self, app_name: str = "par-tts"):
        """Initialize configuration manager.

        Args:
            app_name: Application name for directory creation.
        """
        self.app_name = app_name
        self.config_dir = Path(platformdirs.user_config_dir(app_name))
        self.config_file = self.config_dir / "config.yaml"
        self.config_data: ConfigFile | None = None

    def load_config(self) -> ConfigFile | None:
        """Load configuration from file.

        Returns:
            ConfigFile object if valid config exists, None otherwise.
        """
        if not self.config_file.exists():
            return None

        try:
            with open(self.config_file, encoding="utf-8") as f:
                data = yaml.safe_load(f)

            if not data:
                return None

            # Validate and parse config
            self.config_data = ConfigFile(**data)
            console.print(f"[dim]Loaded config from {self.config_file}[/dim]")
            return self.config_data

        except ValidationError as e:
            console.print(f"[yellow]Warning: Invalid config file: {e}[/yellow]")
            return None
        except Exception as e:
            console.print(f"[yellow]Warning: Could not load config: {e}[/yellow]")
            return None

    def create_sample_config(self) -> None:
        """Create a sample configuration file."""
        sample_lines = [
            "# PAR CLI TTS Configuration File",
            "# Uncomment and modify settings as needed",
            "",
            "# Default provider (elevenlabs, openai, kokoro-onnx)",
            "# provider: kokoro-onnx",
            "",
            "# Default voice (name or ID)",
            "# voice: Rachel",
            "",
            "# Default model",
            "# model: eleven_monolingual_v1",
            "",
            "# Output settings",
            "# output_dir: ~/Documents/audio",
            "# output_format: mp3",
            "# keep_temp: false",
            "# temp_dir: /tmp/par-tts",
            "",
            "# Audio settings",
            "# volume: 1.0",
            "# speed: 1.0",
            "",
            "# ElevenLabs specific",
            "# stability: 0.5",
            "# similarity_boost: 0.5",
            "",
            "# Kokoro ONNX specific",
            "# lang: en-us",
            "",
            "# Behavior settings",
            "# play_audio: true",
            "# debug: false",
        ]

        # Create config directory if it doesn't exist
        self.config_dir.mkdir(parents=True, exist_ok=True)

        # Write sample config
        with open(self.config_file, "w", encoding="utf-8") as f:
            for line in sample_lines:
                f.write(f"{line}\n")

        console.print(f"[green]✓ Created sample config at {self.config_file}[/green]")
        console.print("[dim]Edit this file to set your default preferences[/dim]")

    def merge_with_cli_args(self, **cli_args: Any) -> dict[str, Any]:
        """Merge configuration file with CLI arguments.

        CLI arguments take precedence over config file settings.

        Args:
            **cli_args: Command-line arguments.

        Returns:
            Merged configuration dictionary.
        """
        # Start with config file settings if available
        if self.config_data:
            config_dict = self.config_data.model_dump(exclude_none=True)
        else:
            config_dict = {}

        # Override with CLI arguments (non-None values)
        for key, value in cli_args.items():
            if value is not None:
                config_dict[key] = value

        return config_dict

    def get_value(self, key: str, default: Any = None) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key.
            default: Default value if not found.

        Returns:
            Configuration value or default.
        """
        if self.config_data:
            return getattr(self.config_data, key, default)
        return default
