# PAR CLI TTS

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
![Runs on Linux | MacOS | Windows](https://img.shields.io/badge/runs%20on-Linux%20%7C%20MacOS%20%7C%20Windows-blue)
![Arch x86-63 | ARM | AppleSilicon](https://img.shields.io/badge/arch-x86--64%20%7C%20ARM%20%7C%20AppleSilicon-blue)

![MIT License](https://img.shields.io/badge/license-MIT-green.svg)
![Version](https://img.shields.io/badge/version-0.5.0-green.svg)
![Development Status](https://img.shields.io/badge/status-stable-green.svg)

A text-to-speech library and command-line tool supporting multiple TTS providers (ElevenLabs, OpenAI, Kokoro ONNX, Deepgram, and Google Gemini) with intelligent voice caching, name resolution, and flexible output options.

**Use as a CLI** — `par-tts "Hello world"`
**Use as a library** — `from par_tts import get_provider`

[!["Buy Me A Coffee"](https://www.buymeacoffee.com/assets/img/custom_images/orange_img.png)](https://buymeacoffee.com/probello3)

## Table of Contents

- [What's New](#whats-new)
- [Features](#features)
- [Technology Stack](#technology-stack)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
  - [From PyPI](#installation-from-pypi-recommended)
  - [From Source](#installation-from-source)
  - [Kokoro ONNX Setup](#kokoro-onnx-setup)
- [Using with AI Agents](#using-with-ai-agents)
  - [Claude Code Setup](#claude-code-setup)
  - [Claude Code Output Style](#claude-code-output-style)
- [Configuration](#configuration)
- [Usage](#usage)
- [Command Line Options](#command-line-options)
- [Providers](#providers)
- [Cache Locations](#cache-locations)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)
- [Author](#author)
- [Acknowledgments](#acknowledgments)
- [Support](#support)

## What's New

### v0.5.0
- **Library API surface** — `import par_tts` is now a proper Python library with
  `get_provider()`, `list_providers()`, typed per-provider options, and `SpeechResult`.
  See [Library Usage](#library-usage) for examples.
- **Import package renamed** — canonical import is now `par_tts` (was `par_cli_tts`).
  Old imports still work with a deprecation warning.
- **Decoupled from Rich** — library modules use `stdlib logging` instead of Rich
  console, enabling headless/embedded use without Rich installed.
- **Audio playback extracted** — `play_audio_bytes` and `play_audio_with_player`
  moved to dedicated `par_tts.audio` module.

### v0.4.2
- **Google Gemini TTS provider** - Added `-P gemini` with all 30 prebuilt voices
  (Zephyr, Puck, Kore, Aoede, …) via the `generateContent` audio modality. The
  API returns raw 24 kHz 16-bit mono PCM; the provider wraps it in a WAV header
  so output is a self-contained `.wav`. API key sources, in order:
  `gemini_api_key` in config, `GEMINI_API_KEY` env, or `GOOGLE_API_KEY` env.
- **Deepgram TTS provider** - Added `-P deepgram` with full Aura and Aura-2 voice
  catalog (English, Spanish, Dutch, French, German, Italian, Japanese). Voice
  resolution accepts the full ID (`aura-2-thalia-en`), an ID prefix
  (`aura-2-thalia`), or just the speaker name (`thalia`). API key sources, in
  order: `deepgram_api_key` in config, then `DEEPGRAM_API_KEY` or `DG_API_KEY`
  env vars.
- **Per-provider voice configuration** - New `voices:` mapping in `config.yaml`
  keyed by provider name; switching providers with `-P` no longer inherits a
  voice ID belonging to a different provider.
- **`-y` / `--yes` flag and `--create-config` overwrite confirmation** -
  `--create-config` now prompts before clobbering an existing config; pass `-y`
  to skip the prompt.
- **`--no-play` is now respected** - the config-merge expression that was
  silently coercing it back to `True` has been fixed.

### v0.4.1
- **Claude Code output style installer** - New `install-claude-style` command to automatically set up TTS audio summaries
- **Bundled output style** - TTS Summary output style included with the package

### v0.4.0
- **OpenAI gpt-4o-mini-tts** - New steerable TTS model with `--instructions` option
- **7 new OpenAI voices** - ash, ballad, coral, sage, verse, marin, cedar (13 total)
- **ElevenLabs model updated** - Changed from deprecated `eleven_monolingual_v1` to `eleven_multilingual_v2`
- **Kokoro ONNX 0.5.0** - Updated to latest version

### v0.3.0
- Major code refactoring with better modularity and code organization
- New utility modules for shared console, defaults, and HTTP client
- Test suite with 46 tests for better reliability
- Documentation synced to match current implementation

### v0.2.2
- Updated all HTTP requests and downloaders to ignore SSL certificate errors
- Improves compatibility with corporate proxies and development environments

### v0.2.1
- Updated dependencies
- Ensured Python 3.13 compatibility

### v0.2.0

**Major Update**: Configuration files, smarter caching, consistent error handling, and more!

### New Features
- **Configuration File Support** - Set defaults in `~/.config/par-tts/config.yaml`
- **Smarter Voice Cache** - Change detection, manual refresh, and voice sample caching
- **Consistent Error Handling** - Clear error messages with proper exit codes
- **Multiple Input Methods** - Direct text, stdin piping, and file input (`@filename`)
- **Volume Control** - Adjust playback volume (0.0 to 5.0) across all platforms (macOS, Linux, Windows)
- **Voice Preview** - Test voices with sample text before using

### Improvements
- **Enhanced Security** - API key sanitization in debug output
- **Memory Efficiency** - Stream audio directly to files without buffering
- **Model Verification** - SHA256 checksum verification for downloads
- **Better CLI** - All options now have short versions for quick access
- **Cache Management** - New commands for cache refresh and cleanup

## Features

- **Multiple TTS Providers** - Support for ElevenLabs, OpenAI, Kokoro ONNX, Deepgram (Aura / Aura-2), and Google Gemini with easy provider switching
- **Configuration File** - Set default preferences in YAML config file (`~/.config/par-tts/config.yaml`)
- **Flexible Input Methods** - Accept text from command line, stdin pipe, or files (`@filename`)
- **Voice Name Support** - Use voice names like "Juniper" or "nova" instead of cryptic IDs
- **Volume Control** - Adjust playback volume (0.0 to 5.0) across all platforms (macOS, Linux, Windows)
- **Voice Preview** - Test voices with sample text using `--preview-voice`
- **Smart Voice Caching** - Change detection, auto-refresh, and voice sample caching
- **Partial Name Matching** - Type "char" to match "Charlotte" (ElevenLabs)
- **XDG-Compliant Storage** - Proper cache and data directory management across platforms
- **Rich Terminal Output** - Beautiful colored output with progress indicators
- **Memory Efficient** - Stream audio directly to files without memory buffering
- **Security First** - API keys sanitized in debug output, SHA256 verification for downloads
- **Consistent Error Handling** - Clear error messages with categorized exit codes
- **Provider-Specific Options** - Stability/similarity for ElevenLabs, speed/format for OpenAI
- **Debug Mode** - Comprehensive debugging with sanitized output
- **Smart File Management** - Automatic cleanup or preservation of audio files

## Technology Stack

- **Python 3.11+** - Modern Python with type hints and async support
- **ElevenLabs SDK** - Official ElevenLabs API client for high-quality voices
- **OpenAI SDK** - Official OpenAI API client for TTS
- **Kokoro ONNX** - Offline TTS with ONNX Runtime for fast inference
- **Deepgram REST** - Direct httpx integration for Aura / Aura-2 voices (no SDK)
- **Google Gemini REST** - `generateContent` audio modality with PCM→WAV wrapping (no SDK)
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

### Windows Audio Requirements

For the best audio playback experience on Windows with volume control, install one of these audio players:

#### ffplay (Recommended)
```powershell
# Using Chocolatey
choco install ffmpeg

# Using Scoop
scoop install ffmpeg

# Using winget
winget install ffmpeg
```

#### VLC Media Player (Alternative)
Download from [videolan.org](https://www.videolan.org/vlc/) or:
```powershell
# Using Chocolatey
choco install vlc

# Using winget
winget install VideoLAN.VLC
```

#### mpg123 (Lightweight Option)
```powershell
# Using Chocolatey
choco install mpg123

# Using Scoop
scoop install mpg123
```

**Note**: If no external player is installed, PAR CLI TTS will use Windows PowerShell's built-in MediaPlayer COM object as a fallback. This provides basic playback with volume control (capped at 1.0/100%). For full volume control up to 5.0x, install ffplay, VLC, or mpg123.

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

## Using with AI Agents

PAR CLI TTS works great with AI agents like [Claude Code](https://claude.ai/code). When using it in an agent, you'll need to grant permission for the agent to run the `par-tts` command.

### Claude Code Setup

The easiest way to allow Claude Code to use `par-tts` is to add the following to your `~/.claude/settings.json`:

```json
{
  "permissions": {
    "allow": [
      "Bash(par-tts:*)"
    ]
  }
}
```

This grants Claude Code permission to run any `par-tts` command without prompting for approval each time.

### Example Agent Usage

Once configured, your AI agent can easily generate speech:

```bash
# Agent can run TTS commands directly
par-tts "Task completed successfully!"

# Save audio for notifications
par-tts "Build finished" --output /tmp/notify.mp3 --no-play
```

### Claude Code Output Style

This project includes a **TTS Summary** output style for Claude Code that provides audio announcements when tasks are completed. This creates a personalized audio feedback experience where Claude announces what it has accomplished.

#### Features

- Automatic audio summary at the end of every Claude Code response
- Personalized messages addressing you by name
- Focus on outcomes and user benefits
- Natural, conversational language

#### Installation

The easiest way to install the output style is using the built-in CLI command:

```bash
# Interactive installation (prompts for your name)
par-tts-install-style

# Non-interactive with name specified
par-tts-install-style --name "YourName"

# Force overwrite if already installed
par-tts-install-style --name "YourName" --force
```

This command will:
1. Copy the TTS Summary output style to `~/.claude/output-styles/tts-summary.md`
2. Update `~/.claude/settings.json` with the required `Bash(par-tts:*)` permission
3. Personalize the output style with your name

#### Prerequisites

**Important**: Before using this output style, ensure:

1. `par-cli-tts` is installed (see [Installation](#installation))
2. The `install-claude-style` command has been run (automatically grants permissions)

If you prefer manual installation, you can:
1. Copy `.claude/output-styles/tts-summary.md` to `~/.claude/output-styles/`
2. Add the following to `~/.claude/settings.json`:
   ```json
   {
     "permissions": {
       "allow": [
         "Bash(par-tts:*)"
       ]
     }
   }
   ```

#### Usage

Activate the output style using the `/output-style` command in Claude Code:

```
/output-style tts-summary
```

Once activated, Claude will automatically announce completed tasks with audio feedback.

#### Customization

Edit `~/.claude/output-styles/tts-summary.md` to personalize the experience:

1. **Change your name** - Find the `USER_NAME` variable and update it:
   ```markdown
   ## Variables
   - **USER_NAME**: YourNameHere
   ```

2. **Update the heading** - Search for "Paul" and replace with your name:
   ```markdown
   ## Audio Summary for YourNameHere
   ```

3. **Customize the TTS command** - Use a different voice or provider:
   ```markdown
   par-tts "YourNameHere, task completed." --voice nova --provider openai
   ```

4. **Adjust message style** - Modify the Communication Guidelines section to change how Claude speaks to you

## Configuration

### Configuration File (Recommended)

Create a configuration file to set your default preferences:

```bash
# Create a sample config file (prompts before overwriting if one exists)
par-tts --create-config

# Skip the overwrite prompt with -y / --yes (e.g. for scripted setup)
par-tts --create-config -y

# Edit the config file
$EDITOR ~/.config/par-tts/config.yaml      # macOS: ~/Library/Application\ Support/par-tts/config.yaml
```

Example configuration file:

```yaml
# Default provider (elevenlabs, openai, kokoro-onnx, deepgram, gemini)
provider: kokoro-onnx

# Legacy default voice. Only applied when the active provider matches `provider`
# above — prefer the per-provider `voices:` mapping below for multi-provider use.
voice: Rachel

# Per-provider default voices (recommended). Each entry is used when that provider
# is active (via -P/--provider, TTS_PROVIDER, or `provider` above), regardless of
# which provider this file was originally written for. Takes precedence over `voice`.
voices:
  elevenlabs: Juniper
  openai: nova
  kokoro-onnx: af_sarah
  deepgram: aura-2-thalia-en
  gemini: Kore

# API keys (optional - can also be set via environment variables)
# elevenlabs_api_key: your-elevenlabs-api-key-here
# openai_api_key: your-openai-api-key-here
# deepgram_api_key: your-deepgram-api-key-here
# gemini_api_key: your-google-gemini-api-key-here

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

**Voice resolution order** (highest priority first):

1. CLI `-v` / `--voice` or `TTS_VOICE_ID` env var
2. `voices.<active-provider>` entry in the config file
3. The legacy `voice` field, but only when the active provider equals `config.provider`
4. Provider-specific env var (`ELEVENLABS_VOICE_ID`, `OPENAI_VOICE_ID`, `KOKORO_VOICE_ID`, `DEEPGRAM_VOICE_ID`, `GEMINI_VOICE_ID`)
5. Built-in provider default

This means switching providers with `-P openai` will pick the right voice for that
provider — it will not silently inherit a voice ID belonging to a different one.

### Environment Variables

Create a `.env` file in your project directory with your API keys:

```bash
# Required API keys (at least one for cloud providers)
ELEVENLABS_API_KEY=your_elevenlabs_key_here
OPENAI_API_KEY=your_openai_key_here
DEEPGRAM_API_KEY=your_deepgram_key_here   # DG_API_KEY is also accepted
GEMINI_API_KEY=your_gemini_key_here       # GOOGLE_API_KEY is also accepted

# Optional: Kokoro ONNX model paths (auto-downloads if not set)
# Set these only if you want to use custom model locations
# KOKORO_MODEL_PATH=/path/to/kokoro-v1.0.onnx
# KOKORO_VOICE_PATH=/path/to/voices-v1.0.bin

# Optional: Default provider (elevenlabs, openai, kokoro-onnx, deepgram, or gemini)
TTS_PROVIDER=kokoro-onnx

# Optional: Default voices
ELEVENLABS_VOICE_ID=Juniper            # or use voice ID
OPENAI_VOICE_ID=nova                   # alloy, echo, fable, onyx, nova, shimmer, ...
KOKORO_VOICE_ID=af_sarah               # See available voices with --list
DEEPGRAM_VOICE_ID=aura-2-thalia-en     # Aura/Aura-2 model ID (the model IS the voice)
GEMINI_VOICE_ID=Kore                   # One of 30 prebuilt names (Kore, Zephyr, Aoede, ...)

# Optional: General voice (overrides provider-specific)
TTS_VOICE_ID=Juniper
```

## Usage

### Library Usage

PAR TTS can be used as a Python library in your own projects:

```python
from par_tts import get_provider, list_providers, Voice

# List available providers
print(list_providers())
# ['deepgram', 'elevenlabs', 'gemini', 'kokoro-onnx', 'openai']

# Get a provider class and instantiate it
KokoroTTS = get_provider("kokoro-onnx")
provider = KokoroTTS()  # no API key needed for offline providers

# Generate speech
audio = provider.generate_speech("Hello world", voice="af_sarah")

# Save to file
provider.save_audio(audio, "output.wav")

# List available voices
voices: list[Voice] = provider.list_voices()
for voice in voices:
    print(f"  {voice.id}: {voice.name}")

# Resolve a voice name to an ID
voice_id = provider.resolve_voice("sarah")  # partial match -> "af_sarah"
```

Cloud providers require an API key:

```python
from par_tts import get_provider

OpenAITTS = get_provider("openai")
provider = OpenAITTS(api_key="sk-...")

audio = provider.generate_speech(
    "Hello from OpenAI",
    voice="nova",
    speed=1.2,
)
provider.save_audio(audio, "greeting.mp3")
```

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

# Use OpenAI with voice instructions (gpt-4o-mini-tts only)
par-tts "Hello there!" --provider openai --instructions "Speak in a cheerful and positive tone"
par-tts "Good morning" -P openai -i "Speak like a pirate"

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
| `--provider` | `-P` | TTS provider to use (elevenlabs, openai, kokoro-onnx, deepgram, gemini) | kokoro-onnx |
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
| `--instructions` | `-i` | Voice instructions for gpt-4o-mini-tts (e.g., "Speak cheerfully") | None |

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
| `--create-config` | | Create sample configuration file (prompts before overwriting) | False |
| `--yes` | `-y` | Skip confirmation prompts (e.g. config overwrite) | False |
| `--refresh-cache` | | Force refresh voice cache (ElevenLabs) | False |
| `--clear-cache-samples` | | Clear cached voice samples | False |

## Providers

### ElevenLabs

- **Models**:
  - `eleven_multilingual_v2` (default) - Most lifelike, 29 languages
  - `eleven_v3` - Most expressive, 70+ languages
  - `eleven_flash_v2.5` - Ultra-low latency (~75ms), 32 languages
  - `eleven_turbo_v2.5` - Balanced quality/speed, 32 languages
  - ~~`eleven_monolingual_v1`~~ - Deprecated, will be removed
- **Voices**: 25+ voices with different accents and styles
- **Features**: Voice cloning, stability control, similarity boost
- **Smart Caching**:
  - Automatic 7-day cache for voice listings
  - Change detection via hashing
  - Voice sample caching for offline preview
  - Manual refresh with `--refresh-cache`
- **API Key**: Set `ELEVENLABS_API_KEY` in your .env file

### OpenAI

- **Models**:
  - `gpt-4o-mini-tts` (default) - Steerable TTS with instructions
  - `tts-1` - Optimized for speed
  - `tts-1-hd` - Optimized for quality
- **Voices** (13 total):
  - alloy - Neutral and balanced
  - ash - Enthusiastic and energetic
  - ballad - Warm and soulful
  - coral - Friendly and approachable
  - echo - Smooth and articulate
  - fable - Expressive and animated
  - nova - Warm and friendly (default)
  - onyx - Deep and authoritative
  - sage - Calm and wise
  - shimmer - Soft and gentle
  - verse - Clear and melodic
  - marin - Gentle and soothing
  - cedar - Rich and resonant
- **Features**:
  - Speed control (0.25x to 4x)
  - Multiple output formats
  - Voice instructions for gpt-4o-mini-tts (steer emotion, accent, tone)
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

### Deepgram

- **Models / Voices**: Aura and Aura-2 lines (model and voice are unified — the model
  parameter *is* the voice). Default: `aura-2-thalia-en`.
- **Languages**: English, Spanish, Dutch, French, German, Italian, Japanese
- **Features**:
  - REST `/v1/speak` integration via httpx (no SDK)
  - Streaming chunked download — audio writes to file as it arrives
  - Voice resolution accepts the full ID (`aura-2-thalia-en`), an ID prefix
    (`aura-2-thalia`), or just the speaker name (`thalia`); name lookup prefers
    Aura-2 English, then any Aura-2, then Aura-1
- **Output Formats**: mp3 (default), wav, flac, opus, aac
- **API key**: `deepgram_api_key` in config, or `DEEPGRAM_API_KEY` /
  `DG_API_KEY` env var (the historical Deepgram name is also accepted).
  Get a key at <https://console.deepgram.com>.

### Google Gemini

- **Models**: `gemini-2.5-flash-preview-tts` (default), `gemini-2.5-pro-preview-tts`
- **Voices**: 30 prebuilt voices with style descriptors — Zephyr (Bright),
  Puck (Upbeat), Kore (Firm, default), Aoede (Breezy), Fenrir (Excitable),
  Leda (Youthful), Charon (Informative), Algieba (Smooth), and more.
  Run `par-tts -P gemini --list` for the full table.
- **Features**:
  - REST `generateContent` integration via httpx (no SDK)
  - Single-shot response (not chunked); the provider wraps the raw 24 kHz
    16-bit mono PCM in a 44-byte RIFF/WAVE header so output is a self-contained
    `.wav` file
  - Voice names are case-insensitive on input (`kore`, `Kore`, and `KORE` all
    resolve to the canonical `Kore`)
- **Output Formats**: wav (PCM is the only modality the API emits)
- **API key**: `gemini_api_key` in config, or one of `GEMINI_API_KEY` /
  `GOOGLE_API_KEY` env vars. Get a free key at
  <https://aistudio.google.com/apikey>. (TTS models are currently in preview;
  rate limits and pricing follow the Gemini API tiers.)

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
├── par_tts/                     # Library package (pip install par-cli-tts)
│   ├── __init__.py              # Public API: get_provider, list_providers
│   ├── audio.py                 # Audio playback utilities
│   ├── defaults.py              # Default values for providers
│   ├── errors.py                # TTSError, ErrorType, handle_error
│   ├── http_client.py           # HTTP client factory
│   ├── utils.py                 # Streaming, checksums, sanitization
│   ├── voice_cache.py           # ElevenLabs voice caching
│   ├── model_downloader.py      # Kokoro ONNX model management
│   ├── providers/               # TTS provider implementations
│   │   ├── __init__.py          # PROVIDERS registry
│   │   ├── base.py              # TTSProvider ABC, Voice, SpeechResult, Options
│   │   ├── elevenlabs.py        # ElevenLabs implementation
│   │   ├── openai.py            # OpenAI implementation
│   │   ├── kokoro_onnx.py       # Kokoro ONNX (offline) implementation
│   │   ├── deepgram.py          # Deepgram implementation
│   │   └── gemini.py            # Google Gemini implementation
│   └── cli/                     # CLI-only code (not imported by library users)
│       ├── __init__.py
│       ├── tts_cli.py           # Main CLI application
│       ├── kokoro_cli.py        # Kokoro model management CLI
│       ├── install_claude_style.py  # Claude Code style installer
│       ├── config_file.py       # ConfigManager (YAML)
│       ├── config.py            # TTSConfig dataclass
│       └── console.py           # Rich console instances
├── par_cli_tts/                 # Compat shim (deprecated, re-exports par_tts)
├── tests/
├── pyproject.toml
├── Makefile
├── CLAUDE.md
└── README.md
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
   - On Windows, install ffplay (`choco install ffmpeg`) for best results
   - On Windows without external players, the PowerShell fallback will be used

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
- Starring the repository
- Reporting bugs or requesting features
- Improving documentation
- [Buying me a coffee](https://buymeacoffee.com/probello3)
