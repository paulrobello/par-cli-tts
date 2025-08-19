# PAR CLI TTS

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
![Runs on Linux | MacOS | Windows](https://img.shields.io/badge/runs%20on-Linux%20%7C%20MacOS%20%7C%20Windows-blue)
![Arch x86-63 | ARM | AppleSilicon](https://img.shields.io/badge/arch-x86--64%20%7C%20ARM%20%7C%20AppleSilicon-blue)

![MIT License](https://img.shields.io/badge/license-MIT-green.svg)
![Version](https://img.shields.io/badge/version-0.2.0-green.svg)
![Development Status](https://img.shields.io/badge/status-stable-green.svg)

A powerful command-line text-to-speech tool supporting multiple TTS providers (ElevenLabs, OpenAI, and Kokoro ONNX) with intelligent voice caching, name resolution, and flexible output options.

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/probello3)

## 🆕 What's New in v0.2.0

**✨ Major Update**: Configuration files, smarter caching, consistent error handling, and more!

### New Features
- 📝 **Configuration File Support** - Set defaults in `~/.config/par-tts/config.yaml`
- 🔄 **Smarter Voice Cache** - Change detection, manual refresh, and voice sample caching
- ❌ **Consistent Error Handling** - Clear error messages with proper exit codes
- 📥 **Multiple Input Methods** - Direct text, stdin piping, and file input (`@filename`)
- 🔊 **Volume Control** - Adjust playback volume (0.0 to 5.0) with platform-specific support
- 👂 **Voice Preview** - Test voices with sample text before using

### Improvements
- 🔒 **Enhanced Security** - API key sanitization in debug output
- 🚀 **Memory Efficiency** - Stream audio directly to files without buffering
- ✅ **Model Verification** - SHA256 checksum verification for downloads
- 🎯 **Better CLI** - All options now have short versions for quick access
- 💾 **Cache Management** - New commands for cache refresh and cleanup

## Features

- 🎭 **Multiple TTS Providers** - Support for ElevenLabs, OpenAI, and Kokoro ONNX with easy provider switching
- 📝 **Configuration File** - Set default preferences in YAML config file (`~/.config/par-tts/config.yaml`)
- 📥 **Flexible Input Methods** - Accept text from command line, stdin pipe, or files (`@filename`)
- 🎯 **Voice Name Support** - Use voice names like "Juniper" or "nova" instead of cryptic IDs
- 🔊 **Volume Control** - Adjust playback volume (0.0 to 5.0) with platform-specific support
- 👂 **Voice Preview** - Test voices with sample text using `--preview-voice`
- ⚡ **Smart Voice Caching** - Change detection, auto-refresh, and voice sample caching
- 🔍 **Partial Name Matching** - Type "char" to match "Charlotte" (ElevenLabs)
- 💾 **XDG-Compliant Storage** - Proper cache and data directory management across platforms
- 🎨 **Rich Terminal Output** - Beautiful colored output with progress indicators
- 🚀 **Memory Efficient** - Stream audio directly to files without memory buffering
- 🔒 **Security First** - API keys sanitized in debug output, SHA256 verification for downloads
- ❌ **Consistent Error Handling** - Clear error messages with categorized exit codes
- 🎚️ **Provider-Specific Options** - Stability/similarity for ElevenLabs, speed/format for OpenAI
- 🛠️ **Debug Mode** - Comprehensive debugging with sanitized output
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

### Configuration File (Recommended)

Create a configuration file to set your default preferences:

```bash
# Create a sample config file
par-tts --create-config

# Edit the config file
$EDITOR ~/.config/par-tts/config.yaml
```

Example configuration file:

```yaml
# Default provider (elevenlabs, openai, kokoro-onnx)
provider: kokoro-onnx

# Default voice
voice: Rachel

# Output settings
output_dir: ~/Documents/audio
keep_temp: false

# Audio settings
volume: 1.2
speed: 1.0

# ElevenLabs specific
stability: 0.5
similarity_boost: 0.75

# Behavior settings
play_audio: true
debug: false
```

### Environment Variables

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
TTS_PROVIDER=kokoro-onnx

# Optional: Default voices
ELEVENLABS_VOICE_ID=Juniper  # or use voice ID
OPENAI_VOICE_ID=nova        # alloy, echo, fable, onyx, nova, shimmer
KOKORO_VOICE_ID=af_sarah    # See available voices with --list

# Optional: General voice (overrides provider-specific)
TTS_VOICE_ID=Juniper
```

## Usage

### Quick Start

If installed from PyPI:
```bash
# Simple text-to-speech with default provider
par-tts "Hello, world!"

# Pipe text from another command
echo "Hello from pipe" | par-tts

# Read text from a file
par-tts @input.txt

# Use OpenAI provider
par-tts "Hello" --provider openai --voice nova

# Use ElevenLabs with voice by name
par-tts "Hello" --provider elevenlabs --voice Juniper

# Use Kokoro ONNX (offline, auto-downloads models on first use)
par-tts "Hello" --provider kokoro-onnx --voice af_sarah

# Preview a voice before using it
par-tts --preview-voice Rachel --provider elevenlabs

# Save to file with custom volume
par-tts "Save this" --output audio.mp3 --volume 1.5
```

If running from source:
```bash
# Simple text-to-speech with default provider
uv run par-tts "Hello, world!"

# Use OpenAI provider
uv run par-tts "Hello" --provider openai --voice nova

# Use ElevenLabs with voice by name
uv run par-tts "Hello" --provider elevenlabs --voice Juniper

# Use Kokoro ONNX (offline, auto-downloads models on first use)
uv run par-tts "Hello" --provider kokoro-onnx --voice af_sarah

# Save to file
uv run par-tts "Save this" --output audio.mp3
```

### Basic Examples

```bash
# Simple text-to-speech with default provider (Kokoro ONNX - offline)
par-tts "Hello, world!"

# Input from stdin (pipe)
echo "Hello from stdin" | par-tts
cat script.txt | par-tts --voice nova

# Input from file
par-tts @speech.txt
par-tts @/path/to/long-text.md --provider openai

# Preview voices before using them
par-tts --preview-voice Juniper --provider elevenlabs
par-tts -V af_sarah --provider kokoro-onnx

# Use OpenAI provider
par-tts "Hello from OpenAI" --provider openai --voice nova

# Use ElevenLabs with voice by name
par-tts "Hello from ElevenLabs" --provider elevenlabs --voice Juniper

# Use Kokoro ONNX with language specification
par-tts "Hello from Kokoro" --provider kokoro-onnx --voice af_sarah --lang en-us

# Use partial name matching (ElevenLabs)
par-tts "Hello" --voice char  # matches Charlotte

# Save to file without playing
par-tts "Save this audio" --output audio.mp3 --no-play

# Adjust volume (0.0 = silent, 1.0 = normal, 2.0 = double)
par-tts "Louder please" --volume 1.5
par-tts "Whisper quiet" -w 0.3

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

#### Input Methods

```bash
# Direct text input
par-tts "Direct text input"

# From stdin (automatic detection)
echo "Piped input" | par-tts

# From stdin (explicit)
par-tts - < input.txt

# From file
par-tts @readme.md
par-tts @/absolute/path/to/file.txt

# Chain commands
fortune | par-tts --voice nova
curl -s https://api.example.com/text | par-tts
```

#### Provider Management

```bash
# List available providers
par-tts --list-providers
par-tts -L

# List voices for a specific provider
par-tts --provider openai --list
par-tts -P elevenlabs -l
par-tts --provider kokoro-onnx --list

# Preview voices
par-tts --preview-voice nova --provider openai
par-tts -V Juniper -P elevenlabs

# Show debug information (with sanitized API keys)
par-tts "Test" --debug
par-tts "Test" -d

# Show configuration
par-tts "Test" --dump
par-tts "Test" -D
```

#### Cache Management (ElevenLabs)

```bash
# Force refresh voice cache
par-tts --refresh-cache --provider elevenlabs

# Clear cached voice samples
par-tts --clear-cache-samples --provider elevenlabs

# Or use Makefile commands
make refresh-cache   # Force refresh voice cache
make clear-cache     # Clear voice cache including samples
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
| `--provider` | `-P` | TTS provider to use (elevenlabs, openai, kokoro-onnx) | kokoro-onnx |
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
| `--speed` | `-r` | Speech speed (0.25 to 4.0) | 1.0 |
| `--format` | `-f` | Audio format (mp3, opus, aac, flac, wav) | mp3 |

### Kokoro ONNX Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--lang` | `-g` | Language code (e.g., en-us) | en-us |
| `--speed` | `-r` | Speech speed multiplier | 1.0 |

### File Management

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--keep-temp` | `-k` | Keep temporary audio files after playback | False |
| `--temp-dir` | `-t` | Directory for temporary audio files | System temp |
| `--volume` | `-w` | Playback volume (0.0-5.0, 1.0=normal) | 1.0 |

### Utility Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--debug` | `-d` | Show debug information (API keys sanitized) | False |
| `--dump` | `-D` | Dump configuration and exit | False |
| `--list` | `-l` | List available voices for provider | False |
| `--preview-voice` | `-V` | Preview a voice with sample text | None |
| `--list-providers` | `-L` | List available TTS providers | False |
| `--create-config` | | Create sample configuration file | False |
| `--refresh-cache` | | Force refresh voice cache (ElevenLabs) | False |
| `--clear-cache-samples` | | Clear cached voice samples | False |

## Providers

### ElevenLabs

- **Models**: eleven_monolingual_v1, eleven_multilingual_v1, eleven_multilingual_v2
- **Voices**: 25+ voices with different accents and styles
- **Features**: Voice cloning, stability control, similarity boost
- **Smart Caching**:
  - Automatic 7-day cache for voice listings
  - Change detection via hashing
  - Voice sample caching for offline preview
  - Manual refresh with `--refresh-cache`
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
│   ├── model_downloader.py  # Kokoro model download manager
│   ├── utils.py             # Utility functions (streaming, security)
│   ├── config.py            # Configuration dataclasses
│   ├── config_file.py       # Configuration file management
│   ├── errors.py            # Error handling utilities
│   └── providers/           # TTS provider implementations
│       ├── __init__.py
│       ├── base.py          # Abstract base provider
│       ├── elevenlabs.py    # ElevenLabs implementation
│       ├── openai.py        # OpenAI implementation
│       └── kokoro_onnx.py   # Kokoro ONNX implementation
├── docs/
│   ├── ARCHITECTURE.md      # System architecture documentation
│   └── CLAUDE.md            # Development guidelines
├── .env.example             # Example environment file
├── pyproject.toml           # Project configuration
├── Makefile                 # Development commands
├── CLAUDE.md                # AI assistant context
└── README.md                # This file
```

## Troubleshooting

### Common Issues

1. **API Key Not Found**
   - Ensure your `.env` file contains the correct API keys
   - Check that the `.env` file is in the current directory
   - Verify environment variable names match exactly
   - Note: Kokoro ONNX doesn't require an API key

2. **Voice Not Found**
   - Use `--list` to see available voices for your provider
   - Check spelling and capitalization of voice names
   - For ElevenLabs, use `--refresh-cache` to update voice list

3. **Configuration File Issues**
   - Run `--create-config` to generate a sample config
   - Check file location: `~/.config/par-tts/config.yaml`
   - Verify YAML syntax (use spaces, not tabs)
   - CLI arguments override config file settings

4. **Cache Problems (ElevenLabs)**
   - Force refresh with `--refresh-cache`
   - Clear samples with `--clear-cache-samples`
   - Cache updates automatically detect changes every 24 hours

5. **Audio Not Playing**
   - Ensure you have audio output devices connected
   - Check system volume settings
   - Try adjusting `--volume` flag
   - On Linux, verify audio subsystem (ALSA/PulseAudio) is working

6. **Slow Response Times**
   - Voice previews are cached after first use
   - Use `--debug` to see detailed timing information
   - Kokoro ONNX models download on first use (~106 MB)

7. **File Not Saved**
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
