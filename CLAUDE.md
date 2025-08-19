# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

PAR CLI TTS is a command-line text-to-speech tool supporting multiple TTS providers (ElevenLabs, OpenAI, and Kokoro ONNX). The architecture uses a provider abstraction pattern to enable easy addition of new TTS services while maintaining a consistent interface.

## Development Commands

### Core Development
```bash
# Initial setup (first time)
make setup

# Run linting, formatting, and type checking
make checkall

# Individual checks
make format      # Format with ruff
make lint        # Lint with ruff (auto-fix)
make typecheck   # Type check with pyright

# Update all dependencies
make depsupdate
```

### Running and Testing
```bash
# Run the app with test message
make run
# Or directly: uv run par-tts "Test message"

# Show app help
make app_help

# List available voices
make list-voices

# Voice cache management
make update-cache  # Force update ElevenLabs voice cache
make clear-cache   # Clear cached voice data

# Kokoro ONNX model management
make kokoro-download  # Download Kokoro models
make kokoro-info      # Show model information
make kokoro-clear     # Clear Kokoro models
make kokoro-path      # Show model paths
```

### Package Management
```bash
# Build wheel package
make package

# Build source distribution
make spackage

# Upload to TestPyPI
make test-publish

# Upload to PyPI
make publish
```

## Architecture

### Provider Abstraction Pattern

The codebase uses an abstract base class pattern for TTS providers to enable multiple implementations:

1. **Base Provider (`src/providers/base.py`)**:
   - Defines `TTSProvider` abstract class with required methods
   - All providers must implement: `generate_speech()`, `list_voices()`, `resolve_voice()`, `save_audio()`, `play_audio()`
   - Properties: `name`, `supported_formats`, `default_model`, `default_voice`
   - API key is now optional (for offline providers)
   - Supports both bytes and Iterator[bytes] for streaming audio
   - `play_audio()` now includes volume parameter (0.0-5.0)

2. **Provider Implementations**:
   - `src/providers/elevenlabs.py`: ElevenLabs implementation with voice caching
   - `src/providers/openai.py`: OpenAI TTS implementation
   - `src/providers/kokoro_onnx.py`: Kokoro ONNX offline TTS with automatic model downloading
   - Providers are registered in `src/providers/__init__.py` via the `PROVIDERS` dict

3. **Adding New Providers**:
   - Create new file in `src/providers/`
   - Inherit from `TTSProvider`
   - Implement all abstract methods and properties
   - Register in `PROVIDERS` dict in `__init__.py`
   - Update CLI help text in `src/tts_cli.py`
   - Add provider-specific environment variables if needed

### Voice Caching System

ElevenLabs uses a sophisticated caching system (`src/voice_cache.py`):
- Cache stored in XDG-compliant directories using `platformdirs`
- 7-day expiry for cached voice data
- Automatic cache updates when expired
- Supports name-to-ID resolution with partial matching

### Model Management System

Kokoro ONNX uses automatic model downloading (`src/model_downloader.py`):
- Models stored in XDG-compliant data directories:
  - macOS: `~/Library/Application Support/par-tts-kokoro/`
  - Linux: `~/.local/share/par-tts-kokoro/`
  - Windows: `%LOCALAPPDATA%\par-tts\par-tts-kokoro\`
- Downloads ~106 MB (88 MB int8 quantized model + 18 MB voices)
- Progress indicators with transfer speeds
- Atomic downloads using .tmp files
- SHA256 checksum verification for integrity
- Manual management via `par-tts-kokoro` CLI

### CLI Structure

The main CLI (`src/tts_cli.py`) follows this flow:
1. Input handling (text argument, stdin pipe, or @filename)
2. Provider selection via `--provider` flag or `TTS_PROVIDER` env var
3. Provider instantiation with optional API key from environment
4. Voice resolution (name to ID conversion) or voice preview
5. Speech generation with provider-specific options
6. Audio playback (with volume control) or file saving with smart cleanup

## Key Implementation Patterns

### Provider-Specific Options
Each provider can have unique options that are passed through `**kwargs`:
- ElevenLabs: `stability`, `similarity_boost`
- OpenAI: `speed`, `response_format`
- Kokoro ONNX: `speed`, `lang`
- All providers: `volume` for playback control

These are handled in the main CLI and passed to the provider's methods.

### Input Handling
The CLI supports multiple input methods:
1. Direct text as command argument
2. Automatic stdin detection when piped
3. Explicit stdin with `-` argument
4. File input with `@filename` syntax

### Voice Resolution Strategy
1. Check if input looks like a voice ID (20+ alphanumeric chars for ElevenLabs)
2. For ElevenLabs: Check cache first, update if expired
3. For Kokoro ONNX: Get voices from loaded model
4. Attempt exact name match
5. Fall back to partial name matching
6. Raise error with suggestions if ambiguous

### File Management
- Temporary files use system temp dir by default
- `--temp-dir` creates files in specified directory (always kept)
- `--keep-temp` prevents automatic cleanup
- `--output` specifies exact output path
- Audio streams directly to file without memory buffering
- Cleanup happens in finally block to ensure execution

### Security Features
- API keys are sanitized in debug output using `sanitize_debug_output()`
- SHA256 checksums verify downloaded models
- Sensitive environment variables are masked
- No logging of authentication credentials
- File path validation prevents directory traversal attacks

### Error Handling
The project uses centralized error handling (`src/errors.py`):
- `ErrorType` enum categorizes errors with exit codes
- `handle_error()` provides consistent error messages
- Different exit codes for different error types:
  - 1: User errors (invalid input, missing API key)
  - 2: System errors (network, API, provider)
  - 3: File system errors (permissions, disk full)
  - 4: Configuration errors (config file, cache)

## Configuration

### Configuration File
Settings can be defined in `~/.config/par-tts/config.yaml`:
- Provider defaults: `provider`, `voice`, `model`
- Output settings: `output_dir`, `output_format`, `keep_temp`, `temp_dir`
- Audio settings: `volume`, `speed`
- Provider-specific: `stability`, `similarity_boost`, `lang`
- Behavior: `play_audio`, `debug`

Use `--create-config` to generate a sample configuration file.

### Environment Variables

Required (at least one for cloud providers):
- `ELEVENLABS_API_KEY`: ElevenLabs API key
- `OPENAI_API_KEY`: OpenAI API key

Optional:
- `TTS_PROVIDER`: Default provider (kokoro-onnx/elevenlabs/openai) - defaults to kokoro-onnx
- `TTS_VOICE_ID`: Default voice (overrides provider-specific)
- `ELEVENLABS_VOICE_ID`: Default ElevenLabs voice (defaults to "Juniper")
- `OPENAI_VOICE_ID`: Default OpenAI voice
- `KOKORO_VOICE_ID`: Default Kokoro ONNX voice
- `KOKORO_MODEL_PATH`: Custom path to ONNX model (disables auto-download)
- `KOKORO_VOICE_PATH`: Custom path to voice embeddings (disables auto-download)

### Precedence Order
1. CLI arguments (highest priority)
2. Configuration file settings
3. Environment variables
4. Default values (lowest priority)

## Version Management

Version is stored in `src/__init__.py` and dynamically read by hatchling build system. Update `__version__` there for new releases.

## Type Checking

The project uses strict type checking with pyright. Key patterns:
- Use `str | None` instead of `Optional[str]`
- Support both `bytes` and `Iterator[bytes]` for audio data
- Type all function parameters and returns
- Use `Any` sparingly for provider-specific kwargs
- `# type: ignore` comments should be justified (e.g., SDK quirks)

## New Features (v0.2.0)

### Volume Control
All providers support volume control (0.0-5.0 range):
- macOS: Full support via `afplay -v`
- Linux: Support via `paplay`, `ffplay`, `mpg123`
- Windows: System volume only
- ElevenLabs: Uses built-in player (no volume control)

### Memory-Efficient Streaming
- Providers return `Iterator[bytes]` for streaming
- Audio streams directly to files
- No full audio buffering in memory
- `stream_to_file()` utility function handles streaming

### Input Methods
- Direct text: `par-tts "text"`
- Stdin pipe: `echo "text" | par-tts`
- File input: `par-tts @file.txt`
- Automatic stdin detection when piped

### Voice Preview
- `--preview-voice` or `-V` option
- Tests voice with sample text
- No text argument required

## Testing Providers

When testing provider implementations:
1. Verify API key is loaded correctly (or not needed for offline providers)
2. Test voice resolution with both names and IDs
3. Check audio generation with minimal text
4. Verify file saving and cleanup
5. Test provider-specific options

## Common Issues and Solutions

### Voice Not Found
- ElevenLabs: Cache may be expired, run `make update-cache`
- Kokoro ONNX: Check available voices with `--list`
- Check exact spelling/capitalization
- Use `--list` to see available voices

### Audio Playback Issues
- macOS: Uses `afplay`
- Windows: Uses `start` command
- Linux: Tries `aplay`, `paplay`, `ffplay`, `mpg123` in order

### Slow First Run
- ElevenLabs fetches and caches voice list (7-day expiry)
- Kokoro ONNX downloads models on first use (~106 MB)
- Subsequent runs use cache/local files for faster resolution

### Model Download Issues (Kokoro ONNX)
- Models download from GitHub releases
- If download fails, check internet connection
- Use `par-tts-kokoro download --force` to re-download
- Set `KOKORO_MODEL_PATH` and `KOKORO_VOICE_PATH` to use custom locations
