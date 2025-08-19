# PAR CLI TTS

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
![Runs on Linux | MacOS | Windows](https://img.shields.io/badge/runs%20on-Linux%20%7C%20MacOS%20%7C%20Windows-blue)
![Arch x86-63 | ARM | AppleSilicon](https://img.shields.io/badge/arch-x86--64%20%7C%20ARM%20%7C%20AppleSilicon-blue)

![MIT License](https://img.shields.io/badge/license-MIT-green.svg)
![Version](https://img.shields.io/badge/version-0.1.0-green.svg)
![Development Status](https://img.shields.io/badge/status-stable-green.svg)

A powerful command-line text-to-speech tool supporting multiple TTS providers (ElevenLabs, OpenAI, and Kokoro ONNX) with intelligent voice caching, name resolution, and flexible output options.

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/probello3)

## 🆕 What's New in v0.1.0

**✨ Initial Release**: Multi-provider TTS with ElevenLabs, OpenAI, and Kokoro ONNX support
- 🎭 **Multiple Providers** - Seamless switching between ElevenLabs, OpenAI, and Kokoro ONNX
- 🎯 **Voice Name Resolution** - Use friendly names instead of IDs
- ⚡ **Smart Caching** - 7-day voice cache for ElevenLabs
- 🎨 **Rich Terminal Output** - Beautiful colored output with progress
- 🔊 **Flexible Audio Output** - Play directly or save to file
- 🚀 **Offline Support** - Kokoro ONNX runs locally without API requirements

## Features

- 🎭 **Multiple TTS Providers** - Support for ElevenLabs, OpenAI, and Kokoro ONNX with easy provider switching
- 🎯 **Voice Name Support** - Use voice names like "Rachel" or "nova" instead of cryptic IDs
- ⚡ **Smart Voice Caching** - ElevenLabs voice data cached for 7 days for faster lookups
- 🔍 **Partial Name Matching** - Type "char" to match "Charlotte" (ElevenLabs)
- 💾 **XDG-Compliant Cache** - Proper cache directory management across platforms
- 🎨 **Rich Terminal Output** - Beautiful colored output with progress indicators
- 🔊 **Flexible Audio Output** - Play directly or save to file with custom locations
- 🎚️ **Provider-Specific Options** - Stability/similarity for ElevenLabs, speed/format for OpenAI
- 🛠️ **Debug Mode** - Comprehensive debugging with --debug and --dump options
- 📁 **Smart File Management** - Automatic cleanup or preservation of audio files

## Technology Stack

- **Python 3.11+** - Modern Python with type hints and async support
- **ElevenLabs SDK** - Official ElevenLabs API client for high-quality voices
- **OpenAI SDK** - Official OpenAI API client for TTS
- **Kokoro ONNX** - Offline TTS with ONNX Runtime for fast inference
- **Typer** - Modern CLI framework with automatic help generation
- **Rich** - Terminal formatting and beautiful output
- **Pydantic** - Data validation and settings management
- **Platformdirs** - Cross-platform directory management
- **Python-dotenv** - Environment variable management

## Prerequisites

To install PAR CLI TTS, make sure you have Python 3.11+ installed.

### [uv](https://pypi.org/project/uv/) is recommended

#### Linux and Mac
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

#### Windows
```bash
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

## Installation

### Installation from PyPI (Recommended)

Install the latest stable version using uv:

```bash
uv tool install par-cli-tts
```

Or using pip:

```bash
pip install par-cli-tts
```

After installation, you can run the tool directly:

```bash
# Simple text-to-speech
par-tts "Hello, world!"

# Show help
par-tts --help
```

### Installation From Source

For development or to get the latest features:

1. Clone the repository:
   ```bash
   git clone https://github.com/paulrobello/par-cli-tts.git
   cd par-cli-tts
   ```

2. Install the package dependencies using uv:
   ```bash
   uv sync
   ```

3. Run using uv:
   ```bash
   uv run par-tts "Hello, world!"
   ```

### Kokoro ONNX Setup

Kokoro ONNX models are automatically downloaded on first use! The models are stored in an XDG-compliant data directory:

- **macOS**: `~/Library/Application Support/par-tts/par-tts-kokoro/`
- **Linux**: `~/.local/share/par-tts-kokoro/`
- **Windows**: `%LOCALAPPDATA%\par-tts\par-tts-kokoro\`

#### Automatic Download

When you first use the Kokoro ONNX provider, it will automatically download the required models (~106 MB total using quantized model):

```bash
# Models download automatically on first use
par-tts "Hello" --provider kokoro-onnx
```

#### Manual Model Management

You can also manage models manually using the `par-tts-kokoro` command:

```bash
# Download models manually
par-tts-kokoro download

# Show model information
par-tts-kokoro info

# Show model storage paths
par-tts-kokoro path

# Clear downloaded models
par-tts-kokoro clear

# Force re-download models
par-tts-kokoro download --force
```

#### Using Custom Model Paths

If you prefer to use models from a custom location, set environment variables:

```bash
export KOKORO_MODEL_PATH=/path/to/kokoro-v1.0.onnx
export KOKORO_VOICE_PATH=/path/to/voices-v1.0.bin
```

When these environment variables are set, automatic download is disabled.

## Configuration

Create a `.env` file in your project directory with your API keys:

```bash
# Required API keys (at least one for cloud providers)
ELEVENLABS_API_KEY=your_elevenlabs_key_here
OPENAI_API_KEY=your_openai_key_here

# Optional: Kokoro ONNX model paths (auto-downloads if not set)
# Set these only if you want to use custom model locations
# KOKORO_MODEL_PATH=/path/to/kokoro-v1.0.onnx
# KOKORO_VOICE_PATH=/path/to/voices-v1.0.bin

# Optional: Default provider (elevenlabs, openai, or kokoro-onnx)
TTS_PROVIDER=elevenlabs

# Optional: Default voices
ELEVENLABS_VOICE_ID=Rachel  # or use voice ID
OPENAI_VOICE_ID=nova        # alloy, echo, fable, onyx, nova, shimmer
KOKORO_VOICE_ID=af_sarah    # See available voices with --list

# Optional: General voice (overrides provider-specific)
TTS_VOICE_ID=Rachel
```

## Usage

### Quick Start

If installed from PyPI:
```bash
# Simple text-to-speech with default provider
par-tts "Hello, world!"

# Use OpenAI provider
par-tts "Hello" --provider openai --voice nova

# Use ElevenLabs with voice by name
par-tts "Hello" --voice Rachel

# Use Kokoro ONNX (offline, auto-downloads models on first use)
par-tts "Hello" --provider kokoro-onnx --voice af_sarah

# Save to file
par-tts "Save this" --output audio.mp3
```

If running from source:
```bash
# Simple text-to-speech with default provider
uv run par-tts "Hello, world!"

# Use OpenAI provider
uv run par-tts "Hello" --provider openai --voice nova

# Use ElevenLabs with voice by name
uv run par-tts "Hello" --voice Rachel

# Use Kokoro ONNX (offline, auto-downloads models on first use)
uv run par-tts "Hello" --provider kokoro-onnx --voice af_sarah

# Save to file
uv run par-tts "Save this" --output audio.mp3
```

### Basic Examples

```bash
# Simple text-to-speech with default provider (ElevenLabs)
par-tts "Hello, world!"

# Use OpenAI provider
par-tts "Hello from OpenAI" --provider openai --voice nova

# Use ElevenLabs with voice by name
par-tts "Hello from ElevenLabs" --provider elevenlabs --voice Rachel

# Use Kokoro ONNX with language specification
par-tts "Hello from Kokoro" --provider kokoro-onnx --voice af_sarah --lang en-us

# Use partial name matching (ElevenLabs)
par-tts "Hello" --voice char  # matches Charlotte

# Save to file without playing
par-tts "Save this audio" --output audio.mp3 --no-play

# Adjust ElevenLabs voice settings
par-tts "Stable voice" --stability 0.8 --similarity 0.7

# Adjust OpenAI speech speed
par-tts "Fast speech" --provider openai --speed 1.5

# Keep temp files after playback
par-tts "Keep this" --keep-temp

# Specify custom temp directory (files are kept)
par-tts "Custom location" --temp-dir ./my_audio

# Combine output filename with temp directory
par-tts "Save here" --output my_file.mp3 --temp-dir ./audio_files
```

### Advanced Usage

#### Provider Management

```bash
# List available providers
par-tts "dummy" --list-providers

# List voices for a specific provider
par-tts "dummy" --provider openai --list
par-tts "dummy" --provider elevenlabs --list
par-tts "dummy" --provider kokoro-onnx --list

# Show debug information
par-tts "Test" --debug

# Show configuration
par-tts "Test" --dump
```

#### Output File Behavior

- **With `--output full/path.mp3`**: Saves to exact path specified
- **With `--output filename.mp3 --temp-dir dir`**: Saves to `dir/filename.mp3`
- **With `--temp-dir dir` only**: Saves to `dir/tts_TIMESTAMP.mp3` (kept)
- **With `--keep-temp`**: Temporary files are not deleted after playback
- **Default behavior**: Temp files are auto-deleted after playback

## Command Line Options

### Core Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `text` | | Text to convert to speech (required) | |
| `--provider` | `-P` | TTS provider to use (elevenlabs, openai, kokoro-onnx) | elevenlabs |
| `--voice` | `-v` | Voice name or ID to use | Provider default |
| `--output` | `-o` | Output file path | None (temp file) |
| `--model` | `-m` | Model to use (provider-specific) | Provider default |
| `--play/--no-play` | `-p` | Play audio after generation | --play |

### ElevenLabs Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--stability` | `-s` | Voice stability (0.0 to 1.0) | 0.5 |
| `--similarity` | `-S` | Voice similarity boost (0.0 to 1.0) | 0.5 |

### OpenAI Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--speed` | | Speech speed (0.25 to 4.0) | 1.0 |
| `--format` | `-f` | Audio format (mp3, opus, aac, flac, wav) | mp3 |

### Kokoro ONNX Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--lang` | | Language code (e.g., en-us) | en-us |
| `--speed` | | Speech speed multiplier | 1.0 |

### File Management

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--keep-temp` | `-k` | Keep temporary audio files after playback | False |
| `--temp-dir` | `-t` | Directory for temporary audio files | System temp |

### Utility Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--debug` | `-d` | Show debug information | False |
| `--dump` | `-D` | Dump configuration and exit | False |
| `--list` | `-l` | List available voices for provider | False |
| `--list-providers` | `-L` | List available TTS providers | False |

## Providers

### ElevenLabs

- **Models**: eleven_monolingual_v1, eleven_multilingual_v1, eleven_multilingual_v2
- **Voices**: 25+ voices with different accents and styles
- **Features**: Voice cloning, stability control, similarity boost
- **Caching**: Automatic 7-day cache for voice listings
- **API Key**: Set `ELEVENLABS_API_KEY` in your .env file

### OpenAI

- **Models**: tts-1 (optimized for speed), tts-1-hd (optimized for quality)
- **Voices**:
  - alloy - Neutral and balanced
  - echo - Smooth and articulate
  - fable - Expressive and animated
  - onyx - Deep and authoritative
  - nova - Warm and friendly (default)
  - shimmer - Soft and gentle
- **Features**: Speed control (0.25x to 4x), multiple output formats
- **Output Formats**: mp3, opus, aac, flac, wav, pcm
- **API Key**: Set `OPENAI_API_KEY` in your .env file

### Kokoro ONNX

- **Models**: kokoro-v1.0 (ONNX format, runs locally)
- **Voices**: Multiple voices including af_sarah (default) and others
- **Features**:
  - Offline operation - no API key required
  - Fast CPU/GPU inference with ONNX Runtime
  - Language support with phoneme-based synthesis
  - Speed control
- **Output Formats**: wav, flac, ogg
- **Requirements**:
  - Models auto-download on first use (~106 MB)
  - Uses int8 quantized model for efficiency
  - Stored in XDG-compliant data directory
  - No API key needed - runs entirely locally
  - Manual download available via `par-tts-kokoro download`

## Cache Locations

The ElevenLabs voice cache is stored in platform-specific directories:

- **macOS**: `~/Library/Caches/par-tts-elevenlabs/voice_cache.yaml`
- **Linux**: `~/.cache/par-tts-elevenlabs/voice_cache.yaml`
- **Windows**: `%LOCALAPPDATA%\par-tts-elevenlabs\Cache\voice_cache.yaml`

Cache entries expire after 7 days and are automatically refreshed when needed.

## Development

### Setup Development Environment

```bash
# Clone repository
git clone https://github.com/paulrobello/par-cli-tts.git
cd par-cli-tts

# Install dependencies
uv sync

# Run tests
uv run pytest

# Run linting and formatting
make checkall
```

### Development Commands

```bash
# Format, lint, and type check
make checkall

# Individual commands
make format      # Format with ruff
make lint        # Lint with ruff
make typecheck   # Type check with pyright

# Run the app
make run         # Run with test message
make app_help    # Show app help

# Voice management
make list-voices      # List available voices
make update-cache     # Update voice cache
make clear-cache      # Clear voice cache

# Kokoro ONNX model management
make kokoro-download  # Download Kokoro models
make kokoro-info      # Show model information
make kokoro-clear     # Clear Kokoro models
make kokoro-path      # Show model paths

# Build and package
make package     # Build distribution packages
make clean       # Clean build artifacts
```

### Project Structure

```
par-cli-tts/
├── src/
│   ├── __init__.py
│   ├── tts_cli.py           # Main CLI application
│   ├── voice_cache.py       # Voice caching system
│   └── providers/           # TTS provider implementations
│       ├── __init__.py
│       ├── base.py          # Abstract base provider
│       ├── elevenlabs.py    # ElevenLabs implementation
│       └── openai.py        # OpenAI implementation
├── .env.example             # Example environment file
├── pyproject.toml           # Project configuration
├── Makefile                 # Development commands
└── README.md                # This file
```

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   - Ensure your `.env` file contains the correct API keys
   - Check that the `.env` file is in the current directory
   - Verify environment variable names match exactly

2. **Voice Not Found**
   - Use `--list` to see available voices for your provider
   - Check spelling and capitalization of voice names
   - For ElevenLabs, wait for cache to update or run `make update-cache`

3. **Audio Not Playing**
   - Ensure you have audio output devices connected
   - Check system volume settings
   - On Linux, verify audio subsystem (ALSA/PulseAudio) is working

4. **Slow Response Times**
   - ElevenLabs voice cache may be updating (happens every 7 days)
   - Network connection may be slow
   - Try using `--debug` to see detailed timing information

5. **File Not Saved**
   - Check write permissions for the output directory
   - Ensure the path exists or parent directories can be created
   - Use absolute paths to avoid confusion

### Debug Mode

Enable debug mode for detailed information:

```bash
# Show debug information during execution
par-tts "Test message" --debug

# Dump configuration without executing
par-tts "Test" --dump
```

## Contributing

Contributions are welcome! Please feel free to submit issues, feature requests, or pull requests.

### How to Contribute

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Run tests and checks (`make checkall`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

### Development Guidelines

- Use type hints for all function parameters and returns
- Follow Google-style docstrings
- Ensure all tests pass before submitting PR
- Update documentation for new features
- Keep commits atomic and well-described

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Author

**Paul Robello**  
Email: [probello@gmail.com](mailto:probello@gmail.com)  
GitHub: [@paulrobello](https://github.com/paulrobello)

## Acknowledgments

- [ElevenLabs](https://elevenlabs.io/) for their excellent TTS API
- [OpenAI](https://openai.com/) for their TTS capabilities
- [Typer](https://typer.tiangolo.com/) for the elegant CLI framework
- [Rich](https://rich.readthedocs.io/) for beautiful terminal formatting

## Support

If you find this tool useful, consider:
- ⭐ Starring the repository
- 🐛 Reporting bugs or requesting features
- 📖 Improving documentation
- ☕ [Buying me a coffee](https://buymeacoffee.com/probello3)
