# PAR CLI TTS

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://python.org)
![Runs on Linux | MacOS | Windows](https://img.shields.io/badge/runs%20on-Linux%20%7C%20MacOS%20%7C%20Windows-blue)
![Arch x86-64 | ARM | AppleSilicon](https://img.shields.io/badge/arch-x86--64%20%7C%20ARM%20%7C%20AppleSilicon-blue)

![MIT License](https://img.shields.io/badge/license-MIT-green.svg)
![Version](https://img.shields.io/pypi/v/par-cli-tts.svg)
![Development Status](https://img.shields.io/badge/status-beta-yellow.svg)

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
- [Related Documentation](#related-documentation)
- [License](#license)
- [Author](#author)
- [Acknowledgments](#acknowledgments)
- [Support](#support)

## What's New

### v0.5.1 (Latest)
- **Async library API** -- providers now expose async generation/listing wrappers,
  speech callbacks, and reusable `SpeechPipeline` objects.
- **Expanded public API** -- top-level exports include provider factories,
  typed option schemas, diagnostics, cost estimates, voice search, voice packs,
  retry controls, and Kokoro model management helpers.
- **Provider and workflow polish** -- documentation now reflects provider plugins,
  current CLI workflows, text processing, audio post-processing, and diagnostics.
- **Security and quality fixes** -- HTTP, file, cache, environment, and Windows
  playback handling were tightened based on architecture/security review findings.

For the full version history, see [CHANGELOG.md](CHANGELOG.md).

## Features

- **Multiple TTS Providers** - Support for ElevenLabs, OpenAI, Kokoro ONNX, Deepgram (Aura / Aura-2), and Google Gemini with easy provider switching
- **Configuration File** - Set default preferences in YAML config file (`~/.config/par-tts/config.yaml`) with optional named profiles
- **Flexible Input Methods** - Accept text from command line, stdin pipe, clipboard (`--from-clipboard`), watched stdin (`--watch-stdin`), files (`@filename`), CSV/JSONL batches (`--batch`), or watched document files (`--watch`)
- **Dry Run, Cost Estimate, and Benchmark Modes** - Inspect the resolved operation plan, estimate cloud-provider cost, or compare objective provider latency/size metrics
- **Voice Name Support** - Use voice names like "Juniper" or "nova" instead of cryptic IDs
- **Voice Search** - Search provider voices by name, ID, labels, or category with `--search-voices`
- **Volume Control** - Adjust playback volume (0.0 to 5.0) across all platforms (macOS, Linux, Windows)
- **Voice Preview** - Test voices with sample text using `--preview-voice`
- **Smart Voice Caching** - Change detection, auto-refresh, and voice sample caching
- **Partial Name Matching** - Type "char" to match "Charlotte" (ElevenLabs)
- **XDG-Compliant Storage** - Proper cache and data directory management across platforms
- **Rich Terminal Output** - Beautiful colored output with progress indicators
- **Memory Efficient** - Stream audio directly to files without memory buffering
- **Security First** - API keys sanitized in debug output, SHA256 verification for downloads
- **Consistent Error Handling** - Clear error messages with categorized exit codes
- **Provider-Specific Options** - ElevenLabs voice controls, OpenAI speed/format/instructions, Kokoro speed/language, Deepgram format/sample-rate controls, exposed through validated typed option schemas
- **Async Library API** - Async generation/listing wrappers for integrating providers into async apps without blocking the event loop
- **Event Hooks** - Stable `on_chunk`, `on_progress`, `on_complete`, and `on_error` callbacks for library consumers
- **Reusable Speech Pipelines** - Pre-configured `SpeechPipeline` objects for repeated synthesis in long-running applications
- **Provider Plugins** - Built-in and third-party providers share a plugin registry with capability metadata and entry-point discovery
- **Debug and Structured Logging** - Human-readable debug output or JSON logs for automation/telemetry ingestion
- **Retry Controls** - Per-run or config-file retry/backoff settings for provider generation calls
- **Offline Doctor Diagnostics** - `par-tts doctor` checks audio backends, Kokoro model files, ElevenLabs cache, and API-key environment variables without calling provider APIs
- **Post-Generation Summary** - Compact provider/model/voice, character count, output size, playback, and elapsed-time summary after synthesis
- **Text Processing Pipeline** - Sentence-aware chunking, lightweight SSML-like markup, per-paragraph voice sections, pronunciation dictionaries, and language auto-detection
- **Audio Post-Processing** - Optional ffmpeg-backed normalize, trim-silence, fades, podcast/notification presets, and `--notification` low-latency mode
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

#### Shell completions

Generate shell completion scripts directly from the installed CLI:

```bash
par-tts --completion bash > ~/.local/share/bash-completion/completions/par-tts
par-tts --completion zsh > ~/.zfunc/_par-tts
par-tts --completion fish > ~/.config/fish/completions/par-tts.fish

# Or print shell-specific installation guidance
par-tts --completion-install bash
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

- **macOS**: `~/Library/Application Support/par-tts-kokoro/`
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
2. The `par-tts-install-style` command has been run (automatically grants permissions)

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

# Named profiles override the base settings above when selected with --profile NAME.
profiles:
  podcast:
    provider: openai
    voice: nova
    speed: 0.95
    output_format: mp3
  notifications:
    provider: kokoro-onnx
    voice: af_sarah
    play_audio: true

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
similarity_boost: 0.5

# Text processing
chunk: false
max_chars: 1200
markup: false
voice_sections: false
pronunciations:
  NASA: N A S A
pronunciation_file: ~/pronunciations.yaml
auto_lang: false

# Audio post-processing (requires ffmpeg)
normalize: false
trim_silence: false
post_process_preset: podcast  # podcast or notification
fade_in_ms: 0
fade_out_ms: 0

# Behavior settings
play_audio: true
debug: false

# Reliability / observability
structured_logs: false  # Emit JSON logs for automation/telemetry ingestion
log_level: WARNING      # DEBUG, INFO, WARNING, ERROR, or CRITICAL
retry_attempts: 0       # Retries after the initial provider attempt
retry_backoff: 0.25     # Initial exponential backoff in seconds
```

**Voice resolution order** (highest priority first):

1. CLI `-v` / `--voice` or `TTS_VOICE_ID` env var
2. `voices.<active-provider>` entry in the config file
3. The legacy `voice` field, but only when the active provider equals `config.provider`
4. Provider-specific env var (`ELEVENLABS_VOICE_ID`, `OPENAI_VOICE_ID`, `KOKORO_VOICE_ID`, `DEEPGRAM_VOICE_ID`, `GEMINI_VOICE_ID`)
5. Built-in provider default

This means switching providers with `-P openai` will pick the right voice for that
provider — it will not silently inherit a voice ID belonging to a different one.

#### Config profiles

Profiles let one config file hold multiple workflows. Select one with
`--profile NAME`; the profile values override the base config, and explicit CLI
options still take final precedence.

```bash
par-tts "Welcome back" --profile notifications
par-tts @chapter.md --profile podcast --output chapter.mp3 --no-play
```

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
from par_tts import create_provider, get_provider, list_providers, Voice

# List available providers
print(list_providers())
# ['deepgram', 'elevenlabs', 'gemini', 'kokoro-onnx', 'openai']

# Get a provider class and instantiate it manually
KokoroTTS = get_provider("kokoro-onnx")
provider = KokoroTTS()  # no API key needed for offline providers

# Or use the public factory (reads provider API keys from environment)
provider = create_provider("kokoro-onnx")

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

Async apps can use provider async wrappers. Streamed providers return async
iterators, while single-shot providers return `bytes`:

```python
import asyncio
from collections.abc import AsyncIterator
from par_tts import get_provider

async def main() -> None:
    OpenAITTS = get_provider("openai")
    provider = OpenAITTS(api_key="sk-...")
    audio = await provider.generate_speech_async("Hello async", voice="nova")
    if isinstance(audio, bytes):
        provider.save_audio(audio, "async.mp3")
    else:
        chunks = [chunk async for chunk in audio]
        provider.save_audio(iter(chunks), "async.mp3")

asyncio.run(main())
```

Use typed options and reusable pipelines for repeated requests, including
provider-neutral text processing and ffmpeg-backed audio post-processing:

```python
from par_tts import (
    AudioProcessingOptions,
    OpenAIOptions,
    SpeechCallbacks,
    SpeechPipeline,
    TextProcessingOptions,
)

completed = []
callbacks = SpeechCallbacks(on_complete=completed.append)
pipeline = SpeechPipeline.from_provider_name(
    "openai",
    api_key="sk-...",
    voice="nova",
    options=OpenAIOptions(speed=1.1, response_format="mp3"),
    text_processing=TextProcessingOptions(
        pronunciations={"NASA": "N A S A"},
        chunk=True,
        max_chars=1200,
    ),
    audio_processing=AudioProcessingOptions(normalize=True, preset="podcast"),
    callbacks=callbacks,
)

pipeline.synthesize_to_file("First message", "first.mp3")
pipeline.synthesize_to_file("Second message", "second.mp3")
print(completed[-1].bytes_generated)
```

Callbacks are available as `on_chunk(bytes)`, `on_progress(SpeechProgress)`,
`on_complete(SpeechComplete)`, and `on_error(Exception)`. Provider option schemas
are discoverable with `get_provider_option_schema("openai")`, and
`options_to_kwargs()` converts typed options to `generate_speech()` kwargs.

Other stable public helpers include:

```python
from par_tts import (
    TTSError,
    ErrorType,
    search_voices,
    get_voice_pack,
    load_voice_packs,
    estimate_synthesis_cost,
    collect_diagnostics,
    ModelDownloader,
)

try:
    provider = create_provider("openai")
except TTSError as exc:
    if exc.error_type is ErrorType.MISSING_API_KEY:
        print("Set OPENAI_API_KEY first")

matches = search_voices(provider.list_voices(), "warm")
pack = get_voice_pack("assistant")
estimate = estimate_synthesis_cost("openai", "tts-1", "hello")
diagnostics = collect_diagnostics()
model_info = ModelDownloader().get_model_info()
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

# Inspect, estimate, diagnose, or benchmark before/while generating
par-tts "Hello" --provider openai --dry-run
par-tts "Hello" --provider openai --estimate-cost
par-tts doctor
par-tts --capabilities
par-tts "Hello" --benchmark --benchmark-provider kokoro-onnx --benchmark-provider openai

# Search voices, use named profiles, and inspect built-in voice packs
par-tts --provider openai --search-voices warm
par-tts "Welcome back" --profile notifications
par-tts --list-voice-packs
par-tts --show-voice-pack assistant

# Use clipboard or repeated stdin input
par-tts --from-clipboard --provider openai
printf 'Build complete\nTests passed\n' | par-tts --watch-stdin --provider kokoro-onnx

# Workflow automation
par-tts @template.txt --var name=Paul --var date=2026-04-26 --output greeting.mp3
par-tts --batch prompts.csv --batch-output-dir ./audio --provider openai --no-play
par-tts --watch ./docs --batch-output-dir ./audio --provider kokoro-onnx --no-play
par-tts @narration.md --timestamp-output captions.srt --timestamp-format srt --output narration.mp3 --no-play
par-tts "Build complete" --notification

# Core text/audio processing
par-tts @chapter.md --chunk --max-chars 1200 --output chapter.mp3 --no-play
par-tts 'voice=nova | Hello\n\nvoice=onyx | Goodbye' --voice-sections
par-tts 'NASA says <prosody rate="slow">hello</prosody>' --markup --pronunciation 'NASA=N A S A'
par-tts @narration.md --normalize --trim-silence --post-process-preset podcast --output narration.mp3
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

# From clipboard
par-tts --from-clipboard --voice nova

# Chain commands
fortune | par-tts --voice nova
curl -s https://api.example.com/text | par-tts

# Watch stdin line-by-line until EOF; each non-empty line is synthesized separately
printf 'First alert\nSecond alert\n' | par-tts --watch-stdin --provider kokoro-onnx
```

#### Workflow automation

Batch synthesis accepts `.csv`, `.jsonl`, or `.ndjson` files. Each row/object
needs a text field (`text`, `message`, `script`, or `content`) and can include
`output`, `voice`, `model`, `speed`, `lang`, `response_format`, `stability`,
`similarity_boost`, or `instructions` metadata.

```bash
# CSV: text,voice,output
par-tts --batch prompts.csv --batch-output-dir ./audio --provider openai --no-play

# JSONL: {"text":"Hello","output":"hello.mp3","voice":"nova"}
par-tts --batch prompts.jsonl --batch-output-dir ./audio --provider kokoro-onnx --no-play
```

Template variables render both `{{ name }}` and `{name}` placeholders in
`@file` input, batch row text, and watched files:

```bash
par-tts @template.txt --var name=Paul --var date=2026-04-26 --output greeting.mp3
```

Docs-to-audio watch mode accepts a single file or a folder containing `.md`,
`.markdown`, `.txt`, or `.rst` files. It regenerates `stem.mp3` files in
`--batch-output-dir`; use `--watch-once` for one-shot automation/tests.

```bash
par-tts --watch ./docs --batch-output-dir ./audio --provider kokoro-onnx --no-play
par-tts --watch ./docs/intro.md --watch-once --batch-output-dir ./audio --no-play
```

Timestamp export writes rough sentence timings for video workflows:

```bash
par-tts @narration.md --output narration.mp3 --timestamp-output captions.json --timestamp-format json --no-play
par-tts @narration.md --output narration.mp3 --timestamp-output captions.srt --timestamp-format srt --no-play
```

Notification mode applies short-message defaults: OpenAI uses `tts-1`, speech
speed is raised to `1.15`, and notification post-processing/trim-silence are
enabled.

```bash
par-tts "Build complete" --notification
```

#### Built-in voice packs

Voice packs are bundled metadata-only recommendations for common use cases such
as alerts, assistants, narration, and storytelling. They do not contact provider
APIs or create audio until you choose one of the recommended provider/voice
combinations for a normal synthesis command.

```bash
# List all bundled packs
par-tts --list-voice-packs

# Show provider, voice, model, and notes for one pack
par-tts --show-voice-pack assistant
```

#### Provider Management

```bash
# List available providers and static provider capabilities
par-tts --list-providers
par-tts -L
par-tts --capabilities

# List voices for a specific provider
par-tts --provider openai --list
par-tts -P elevenlabs -l
par-tts --provider kokoro-onnx --list

# Preview and search voices
par-tts --preview-voice nova --provider openai
par-tts -V Juniper -P elevenlabs
par-tts --provider openai --search-voices warm

# Show debug information (with sanitized API keys) or structured JSON logs
par-tts "Test" --debug
par-tts "Test" -d
par-tts "Test" --structured-logs --log-level INFO

# Retry provider generation after transient failures
par-tts "Test" --provider openai --retry-attempts 2 --retry-backoff 0.5

# Run offline diagnostics without provider API calls
par-tts doctor

# Show configuration, planned execution, cost, or benchmark metrics
par-tts "Test" --dump
par-tts "Test" -D
par-tts "Test" --dry-run
par-tts "Test" --provider openai --estimate-cost
par-tts "Test" --benchmark --benchmark-repeat 3 --benchmark-provider kokoro-onnx
```

#### Cache Management (ElevenLabs)

```bash
# Force refresh voice cache
par-tts --refresh-cache --provider elevenlabs

# Clear cached voice samples
par-tts --clear-cache-samples --provider elevenlabs

# Or use Makefile commands
make update-cache    # Force refresh voice cache
make clear-cache     # Clear voice cache including samples
```

#### Output File Behavior

- **With `--output full/path.mp3`**: Saves to exact path specified
- **With `--output filename.mp3 --temp-dir dir`**: Saves to `dir/filename.mp3`
- **With `--temp-dir dir` only**: Saves to `dir/tts_TIMESTAMP.mp3` (kept)
- **With `--keep-temp`**: Temporary files are not deleted after playback
- **Default behavior**: Temp files are auto-deleted after playback

#### Text processing pipeline

PAR TTS can preprocess input before synthesis:

- `--chunk --max-chars N` splits long input on paragraph/sentence boundaries and synthesizes each chunk.
- `--markup` parses a small SSML-like subset: `<break time="500ms"/>`, `[pause=500ms]`, `<prosody rate="slow|fast|1.2">...</prosody>`, and `<emphasis>...</emphasis>`.
- `--voice-sections` parses paragraph prefixes like `voice=nova; speed=1.1; lang=en-us | Text` so each section can use different voice/style metadata.
- `--pronunciation WORD=spoken` can be repeated; `--pronunciation-file file.yaml` loads a YAML mapping.
- `--auto-lang` uses no-dependency script heuristics to pass language hints where providers support them.

When multiple chunks/sections are written to one `--output`, PAR TTS uses ffmpeg to join the generated segment files.

#### Audio post-processing

Audio post-processing is file-based and requires `ffmpeg`:

```bash
par-tts @chapter.md --output chapter.mp3 --normalize --trim-silence --no-play
par-tts "Build complete" --post-process-preset notification
par-tts @podcast.md --post-process-preset podcast --fade-in-ms 100 --fade-out-ms 250
```

Supported controls are `--normalize`, `--trim-silence`, `--fade-in-ms`,
`--fade-out-ms`, and `--post-process-preset podcast|notification`.

#### Post-generation summary

Every successful synthesis prints a compact summary line with the provider,
model, resolved voice, character count, output location/size when available,
playback status, and elapsed generation/playback time.

## Command Line Options

### Core Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `text` | | Text to convert to speech (required) | |
| `--provider` | `-P` | TTS provider to use (elevenlabs, openai, kokoro-onnx, deepgram, gemini) | kokoro-onnx |
| `--voice` | `-v` | Voice name or ID to use | Provider default |
| `--output` | `-o` | Output file path | None (temp file) |
| `--model` | `-m` | Model to use (provider-specific) | Provider default |
| `--profile` | | Named config profile to apply | None |
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

### Text Processing Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--chunk` | | Split long input into sentence-aware chunks | False |
| `--max-chars` | | Maximum characters per chunk when `--chunk` is enabled | 1200 |
| `--markup` | | Parse lightweight SSML-like markup | False |
| `--voice-sections` | | Parse per-paragraph `voice=... | text` sections | False |
| `--pronunciation` | | Pronunciation replacement as `WORD=spoken`; repeatable | None |
| `--pronunciation-file` | | YAML mapping file of pronunciation replacements | None |
| `--auto-lang` | | Detect input language with script heuristics | False |

### Audio Post-Processing Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--normalize` | | Normalize generated audio with ffmpeg | False |
| `--trim-silence` | | Trim leading silence with ffmpeg | False |
| `--post-process-preset` | | Post-processing preset (`podcast` or `notification`) | None |
| `--fade-in-ms` | | Fade-in duration in milliseconds | 0 |
| `--fade-out-ms` | | Fade-out duration in milliseconds | 0 |

### Utility Options

| Option | Short | Description | Default |
|--------|-------|-------------|---------|
| `--debug` | `-d` | Show debug information (API keys sanitized) | False |
| `--structured-logs` | | Emit JSON logs for automation/telemetry ingestion | False |
| `--log-level` | | Logging level (`DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`) | `DEBUG` with `--debug`, otherwise `WARNING` |
| `--retry-attempts` | | Retries after the initial provider generation attempt | 0 |
| `--retry-backoff` | | Initial exponential retry backoff in seconds | 0.0 |
| `doctor` | | Offline diagnostics pseudo-command: audio backends, Kokoro models, ElevenLabs cache, env vars | |
| `--dump` | `-D` | Dump configuration and exit | False |
| `--dry-run` | | Show the resolved operation plan without generating speech | False |
| `--estimate-cost` | | Estimate synthesis cost without generating speech | False |
| `--capabilities` | | Show provider formats, controls, streaming support, and API key requirements | False |
| `--completion` | | Print shell completion script for `bash`, `zsh`, or `fish` and exit | None |
| `--completion-install` | | Print shell-specific completion installation instructions and exit | None |
| `--list-voice-packs` | | List bundled voice-pack recommendations and exit | False |
| `--show-voice-pack` | | Show one bundled voice pack by name and exit | None |
| `--benchmark` | | Run objective provider benchmark for the input text | False |
| `--benchmark-provider` | | Provider to include in `--benchmark`; repeatable | `--provider` |
| `--benchmark-repeat` | | Number of benchmark synthesis runs per provider | 1 |
| `--from-clipboard` | | Read input text from the system clipboard | False |
| `--watch-stdin` | | Read stdin line-by-line and synthesize each non-empty line until EOF | False |
| `--batch` | | CSV/JSONL batch input with text plus optional metadata | None |
| `--batch-output-dir` | | Directory for batch/watch generated audio files | Current directory |
| `--var` | | Template variable as `KEY=VALUE`; repeatable | None |
| `--watch` | | Watch a text file/folder and regenerate audio when documents change | None |
| `--watch-once` | | Process current `--watch` inputs once, then exit | False |
| `--watch-interval` | | Polling interval in seconds for `--watch` | 1.0 |
| `--timestamp-output` | | Write rough timing metadata to JSON or SRT | None |
| `--timestamp-format` | | Timestamp export format (`json` or `srt`) | json |
| `--notification` | | Apply low-latency defaults for short notification messages | False |
| `--list` | `-l` | List available voices for provider | False |
| `--search-voices` | | Search voices by name, ID, labels, or category | None |
| `--preview-voice` | `-V` | Preview a voice with sample text | None |
| `--list-providers` | `-L` | List available TTS providers | False |
| `--create-config` | | Create sample configuration file (prompts before overwriting) | False |
| `--yes` | `-y` | Skip confirmation prompts (e.g. config overwrite) | False |
| `--refresh-cache` | | Force refresh voice cache (ElevenLabs) | False |
| `--clear-cache-samples` | | Clear cached voice samples | False |

## Providers

### Provider plugins

Providers are discovered through plugin descriptors. The bundled providers are
registered as built-in plugins, and third-party packages can expose additional
providers with the Python entry point group `par_tts.providers`.

A plugin entry point may load one of:

- a `par_tts.providers.ProviderPlugin` object
- a zero-argument factory returning `ProviderPlugin`
- a `TTSProvider` subclass with metadata attributes such as `plugin_name`,
  `plugin_description`, `plugin_capabilities`, `plugin_default_model`, and
  `plugin_requires_api_key`

Example third-party `pyproject.toml`:

```toml
[project.entry-points."par_tts.providers"]
my-provider = "my_package.tts:provider_plugin"
```

Use `par-tts --capabilities` to see built-in and installed plugin capabilities
without initializing providers or requiring API keys. Bad third-party plugins are
isolated and reported as diagnostics instead of preventing built-ins from loading.

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

| Path | Purpose |
|------|---------|
| `par_tts/__init__.py` | Public library API for providers, pipelines, options, callbacks, diagnostics, costs, and helper functions |
| `par_tts/audio.py` | Cross-platform audio playback utilities |
| `par_tts/audio_processing.py` | `ffmpeg`-backed normalization, silence trimming, fades, presets, and file concatenation |
| `par_tts/cli/` | CLI entry points, config-file handling, shell completions, Kokoro management, and Claude Code style installation |
| `par_tts/costs.py` | Static synthesis cost estimates used by CLI and library helpers |
| `par_tts/defaults.py` | Provider defaults for voices and models |
| `par_tts/diagnostics.py` | Offline diagnostic checks for audio backends, model files, cache state, and API-key environment variables |
| `par_tts/errors.py` | `TTSError`, categorized exit codes, path validation, and user-facing error handling |
| `par_tts/http_client.py` | Shared HTTP client factory for API providers |
| `par_tts/logging_config.py` | Human-readable and structured JSON logging configuration |
| `par_tts/model_downloader.py` | Kokoro ONNX model download, verification, and cleanup |
| `par_tts/pipeline.py` | Reusable `SpeechPipeline` orchestration for library consumers |
| `par_tts/provider_factory.py` | Public provider factory that resolves provider plugins and API keys |
| `par_tts/providers/` | Built-in provider implementations, base abstractions, typed options, callbacks, and plugin registry |
| `par_tts/retry.py` | Retry/backoff policy for provider generation calls |
| `par_tts/text_processing.py` | Chunking, lightweight markup, voice sections, pronunciations, and language hints |
| `par_tts/utils.py` | Streaming, checksum verification, safe debug output, and environment sanitization |
| `par_tts/voice_cache.py` | ElevenLabs voice metadata and sample caching |
| `par_tts/voice_packs.py` | Built-in metadata-only voice-pack recommendations |
| `par_tts/voice_search.py` | Provider-neutral voice search helpers |
| `par_tts/workflow.py` | Batch synthesis, watched-file processing, templating, and timestamp export helpers |
| `par_cli_tts/` | Deprecated compatibility shim that re-exports `par_tts` |
| `tests/` | Pytest suite |
| `docs/` | Architecture and documentation style guidance |
| `pyproject.toml` | Package metadata, dependencies, scripts, and build configuration |
| `Makefile` | Development, verification, package, and maintenance commands |

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

## Related Documentation

- [Architecture](docs/ARCHITECTURE.md) - Provider architecture, CLI flow, data storage, and extension points
- [Documentation Style Guide](docs/DOCUMENTATION_STYLE_GUIDE.md) - Project documentation standards
- [Changelog](CHANGELOG.md) - Release history and notable changes
- [Contributing](CONTRIBUTING.md) - Contribution workflow and development expectations
- [Security Policy](SECURITY.md) - Supported versions and vulnerability reporting

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
