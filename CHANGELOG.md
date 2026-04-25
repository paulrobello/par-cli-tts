# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Google Gemini TTS provider** (`-P gemini`) — Gemini API
  `generateContent` with `responseModalities: ["AUDIO"]` integration via httpx
  (no SDK). All 30 prebuilt voices (Zephyr, Puck, Kore, Aoede, …) with style
  descriptors. The API returns raw 16-bit mono PCM at 24 kHz; the provider
  prepends a RIFF/WAVE header so output is a self-contained `.wav` file. API
  key sources, in order: `gemini_api_key` in config, `GEMINI_API_KEY` env
  var, then `GOOGLE_API_KEY` env var (the Google AI Studio default name).
  New `gemini` key supported in the per-provider `voices:` mapping. Default
  voice: `Kore`. Default model: `gemini-2.5-flash-preview-tts`.

- **Deepgram TTS provider** (`-P deepgram`) — REST `/v1/speak` integration via httpx
  (no SDK dependency). Supports the full Aura and Aura-2 voice catalog (English,
  Spanish, Dutch, French, German, Italian, Japanese). Voice resolution accepts the
  full ID (`aura-2-thalia-en`), an ID prefix (`aura-2-thalia`), or just the speaker
  name (`thalia`, prefers Aura-2 English first). API key sources, in order:
  `deepgram_api_key` in config, `DEEPGRAM_API_KEY` env var, or `DG_API_KEY` env var
  (the historical Deepgram convention). New `deepgram` key supported in the
  per-provider `voices:` mapping. Default voice: `aura-2-thalia-en`.

- **`-y` / `--yes` flag** — answer yes to confirmation prompts (currently used by
  `--create-config` to suppress the new overwrite prompt for scripted setup).

- **Per-provider voice configuration** — new `voices:` mapping in `config.yaml`
  - Keyed by provider name (`elevenlabs`, `openai`, `kokoro-onnx`)
  - Used whenever that provider is active, regardless of which provider the config
    was originally written for (so `-P openai` no longer inherits an ElevenLabs voice ID)
  - Takes precedence over the legacy global `voice` field
  - Unknown provider keys are rejected at config-load time
  - Example:
    ```yaml
    voices:
      elevenlabs: Juniper
      openai: nova
      kokoro-onnx: af_sarah
    ```

### Changed

- **Package layout** — internal package renamed from `src` to `par_cli_tts` for a
  proper, importable PyPI-style name. No public CLI/API surface change; only
  affects direct internal imports (e.g. `from par_cli_tts.providers.base import ...`).
- **Dependency version floors raised** to current upstream majors:
  - Runtime: `elevenlabs>=2.44`, `openai>=2.32`, `rich>=15`, `typer>=0.24`,
    `python-dotenv>=1.2`, `platformdirs>=4.9`, `pyyaml>=6.0.3`
  - Dev: `pytest>=9`, `pytest-cov>=7`, `ruff>=0.15`, `pyright>=1.1.409`,
    `pre-commit>=4.6`, `build>=1.4`, `hatchling>=1.29`

### Fixed

- **`--no-play` is now respected** — previously the config-file merge expression
  silently coerced an explicit `--no-play` (False) back to True whenever the
  config file did not set `play_audio`. Audio now stays silent when the user asks
  for it to. `--play` (the default) still falls through to `config.play_audio`
  when set.

- **`--create-config` no longer silently overwrites an existing config** — it now
  prompts for confirmation; pass `-y`/`--yes` to skip.

- **Voice bleed across providers** — overriding only `-P/--provider` (or `TTS_PROVIDER`)
  no longer applies the config's `voice`/`model` fields to the new provider when
  they were intended for a different one. Voice falls through to the new provider's
  default (or the per-provider entry in the new `voices:` mapping if set).

## [0.4.2] - 2025-03-02

### Fixed

- **Config file provider setting** - Provider from config file now correctly overrides default
  - CLI was defaulting to `kokoro-onnx` instead of reading `provider` from config
  - Fixed by changing CLI default from `DEFAULT_PROVIDER` to `None`

- **API keys in config file** - API keys can now be stored in config file
  - Added `elevenlabs_api_key` and `openai_api_key` fields to config schema
  - Config file takes precedence over environment variables

- **ElevenLabs audio playback** - Fixed volume control and iterator consumption
  - Replaced SDK's `play()` with system player for volume support
  - Fixed import path for `play`/`save` (moved to `elevenlabs.play` submodule)
  - Fixed iterator being consumed by `save_audio()` before `play_audio()`

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
