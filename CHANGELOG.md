# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
