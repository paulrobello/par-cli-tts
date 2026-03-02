# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.4.1] - 2025-03-02

### Added

- **Claude Code output style installer** - New `par-tts-install-style` command
  - Automatically installs TTS Summary output style to `~/.claude/output-styles/`
  - Updates `~/.claude/settings.json` with `Bash(par-tts:*)` permission
  - Prompts for user name to personalize audio summaries
  - Use `--name` option to skip prompt, `--force` to overwrite existing
  - Cross-platform compatible (Windows, macOS, Linux)
  - Handles missing directories and corrupt settings.json gracefully

- **Bundled TTS Summary output style** - Included `.claude/output-styles/tts-summary.md`
  - Personalized audio task completion announcements
  - Clear instructions for Claude to execute TTS commands
  - Customizable user name and communication style

## [0.4.0] - 2025-03-02

### Added

- **OpenAI gpt-4o-mini-tts model support** with steerable voice instructions
  - New `--instructions` / `-i` option for voice style control
  - Example: `par-tts "Hello" --instructions "Speak in a cheerful tone"`
  - Supports emotional steering, accents, and tone control

- **7 new OpenAI voices** added to the voice list:
  - ash - Enthusiastic and energetic
  - ballad - Warm and soulful
  - coral - Friendly and approachable
  - sage - Calm and wise
  - verse - Clear and melodic
  - marin - Gentle and soothing
  - cedar - Rich and resonant

### Changed

- **ElevenLabs default model updated** from deprecated `eleven_monolingual_v1` to `eleven_multilingual_v2`
  - Old model was deprecated and scheduled for removal by ElevenLabs
  - New model supports 29 languages with better quality

- **OpenAI default model updated** from `tts-1` to `gpt-4o-mini-tts`
  - New model offers better quality and steerable voice control
  - Legacy `tts-1` and `tts-1-hd` models still available via `--model`

- **Kokoro ONNX dependency updated** from `>=0.4.9` to `>=0.5.0`

### Deprecated

- ElevenLabs `eleven_monolingual_v1` model (will be removed by provider)

## [0.3.0] - 2025-03-02

### Added

- **New utility modules** for better code organization
  - `src/console.py` - Shared Rich console instance for consistent output
  - `src/defaults.py` - Central default values for providers
  - `src/http_client.py` - HTTP client factory for consistent configuration

- **Test suite** with 46 tests covering:
  - Utility functions (voice ID detection, debug sanitization, checksums, streaming)
  - Configuration modules (dataclasses and Pydantic models)
  - Voice cache operations

### Changed

- **Major refactor of `tts_cli.py`** - Extracted 588-line `main()` into focused helper functions:
  - `get_provider_kwargs()` - Build provider-specific kwargs
  - `handle_config_operations()` - Config creation/dumping
  - `handle_input_operations()` - Input handling (stdin/file/argument)
  - `handle_list_providers()` / `handle_list_voices()` - Listing operations
  - `handle_voice_preview()` - Voice preview functionality
  - `handle_speech_generation()` - Core TTS generation

- **Eliminated code duplication**:
  - Audio playback logic consolidated in `src/utils.py`
  - HTTP client creation consolidated in `src/http_client.py`
  - Default voice definitions consolidated in `src/defaults.py`
  - Console instances consolidated in `src/console.py`
  - Voice ID detection utility in `src/utils.py`

- **Documentation sync** - Updated all docs to match current implementation

### Fixed

- Suppress ElevenLabs Pydantic V1 deprecation warning

## [0.2.2] - 2025-01-XX

### Added

- SSL certificate verification bypass for environments with certificate issues

## [0.2.0] - 2025-01-XX

### Added

- Volume control for audio playback (0.0-5.0 range)
- Memory-efficient streaming for audio generation
- Multiple input methods (direct text, stdin pipe, file input with @filename)
- Voice preview feature (`--preview-voice` / `-V`)
- Kokoro ONNX provider with automatic model downloading
- Configuration file support (`~/.config/par-tts/config.yaml`)

### Changed

- Provider abstraction pattern for easy addition of new TTS services
- API keys now optional (for offline providers like Kokoro)
- Improved error handling with categorized exit codes
