PAR CLI TTS v0.2.0 released! 🎉 Major update with config files, consistent error handling, smarter caching, stdin/file input, volume control, voice preview, and memory-efficient streaming for multi-provider text-to-speech.

# What My Project Does:

PAR CLI TTS is a powerful command-line text-to-speech tool that provides a unified interface for multiple TTS providers including ElevenLabs, OpenAI, and Kokoro ONNX (offline). It features intelligent voice caching, friendly name resolution, and flexible output options. The tool seamlessly switches between cloud and offline providers while maintaining a consistent user experience.

# What's New:

### v0.2.0 - Major Feature Update

📝 **Configuration File Support**: Set your defaults once and forget
  - YAML config at `~/.config/par-tts/config.yaml`
  - `--create-config` generates a sample configuration
  - Set default provider, voice, volume, output directory, and more
  - CLI arguments still override config file settings
  - Finally, no more typing the same options repeatedly!

❌ **Consistent Error Handling**: Clear, categorized error messages
  - ErrorType enum with proper exit codes
  - Helpful error messages with suggestions
  - Debug mode shows detailed stack traces
  - Errors categorized (AUTH, NETWORK, VOICE, FILE, etc.)
  - No more cryptic Python tracebacks!

🔄 **Smarter Voice Cache**: Enhanced caching with change detection
  - Automatic change detection via content hashing
  - Manual cache refresh with `--refresh-cache`
  - Voice sample caching for offline preview
  - Clear samples with `--clear-cache-samples`
  - Cache knows when provider updates voices!

📥 **Multiple Input Methods**: Flexible text input options for any workflow
  - Automatic stdin detection: `echo "text" | par-tts`
  - Explicit stdin: `par-tts -` 
  - File input: `par-tts @speech.txt`
  - Direct text still supported: `par-tts "Hello world"`

🔊 **Volume Control**: Platform-specific playback volume adjustment
  - Range from 0.0 (silent) to 5.0 (5x volume)
  - macOS: Full support via `afplay -v`
  - Linux: Support via `paplay`, `ffplay`, `mpg123`
  - New `-w/--volume` flag for easy control

👂 **Voice Preview**: Test voices before using them
  - `--preview-voice` or `-V` option
  - Plays sample text with selected voice
  - Cached samples for instant replay
  - No text argument required for preview mode
  - Perfect for exploring available voices

🚀 **Memory-Efficient Streaming**: Reduced memory footprint
  - Stream audio directly to files using Iterator[bytes]
  - No full audio buffering in memory
  - Significant performance improvement for large files
  - Provider abstraction updated to support streaming

🔒 **Enhanced Security**: Safer debug output
  - API keys automatically sanitized in debug mode
  - SHA256 checksum verification for downloaded models
  - Sensitive environment variables masked
  - No logging of authentication credentials

🎯 **Better CLI Experience**: All options now have short flags
  - Every command option has a short version for quick access
  - Consistent flag naming across all features
  - Example: `-P` provider, `-v` voice, `-w` volume, `-V` preview

### v0.1.0 - Initial Release Features

* Multi-provider support (ElevenLabs, OpenAI, Kokoro ONNX)
* Intelligent voice name resolution with partial matching
* 7-day voice cache for ElevenLabs optimization
* XDG-compliant cache and data directories
* Automatic model downloading for offline providers
* Rich terminal output with progress indicators
* Provider-specific options (stability, speed, format)

# Key Features:

* **📝 Configuration Files**: Set defaults in YAML config, no more repetitive typing
* **🎭 Multiple TTS Providers**: Seamless switching between ElevenLabs, OpenAI, and Kokoro ONNX
* **📥 Flexible Input**: Accept text from command line, stdin pipe, or files (@filename)
* **🔊 Volume Control**: Adjust playback volume (0.0-5.0) with platform-specific support
* **👂 Voice Preview**: Test voices with sample text and caching for instant replay
* **🎯 Smart Voice Resolution**: Use friendly names like "Juniper" instead of cryptic IDs
* **⚡ Intelligent Caching**: Smart cache with change detection, manual refresh, and voice samples
* **🚀 Offline Support**: Kokoro ONNX runs entirely locally with auto-downloading models
* **🔒 Secure by Default**: API keys in environment variables, sanitized debug output
* **❌ Consistent Errors**: Categorized error handling with helpful messages
* **📊 Rich Terminal UI**: Beautiful colored output with progress indicators
* **💾 Smart File Management**: Automatic cleanup or preservation of audio files
* **🎚️ Provider Options**: Fine-tune with stability, similarity, speed, and format settings
* **🚀 Memory Efficient**: Stream processing with Iterator[bytes] for minimal memory usage

# Why It's Better:

Unlike single-provider TTS tools, PAR CLI TTS offers:
- **Configuration Management**: Set your preferences once in a YAML file - no more long command lines
- **Provider Independence**: Not locked to one service - switch providers without changing workflow
- **Offline Capability**: Kokoro ONNX provides high-quality TTS without internet or API keys
- **Voice Name Resolution**: No need to remember voice IDs - use friendly names with fuzzy matching
- **Smart Caching**: Cache detects changes, stores voice samples, and refreshes intelligently
- **Memory Efficiency**: Stream processing means minimal memory usage even for large texts
- **Error Excellence**: Categorized errors with helpful messages instead of Python tracebacks
- **Security First**: API keys never exposed, debug output automatically sanitized
- **True CLI Design**: Every feature accessible via short flags, pipes, and standard Unix patterns

# GitHub and PyPI

* PAR CLI TTS is under active development with regular feature updates
* Check out the project on GitHub for full documentation and contribution guidelines: [https://github.com/paulrobello/par-cli-tts](https://github.com/paulrobello/par-cli-tts)
* PyPI: [https://pypi.org/project/par-cli-tts/](https://pypi.org/project/par-cli-tts/)
* Installation: `pip install par-cli-tts` or `uv tool install par-cli-tts`

# Comparison:

While there are many TTS libraries and tools available, PAR CLI TTS is unique in providing:
- **Configuration file support** with YAML-based defaults (set once, use everywhere)
- **Unified interface** across multiple providers (not just a wrapper for one service)
- **Intelligent voice caching** with change detection and sample storage (no other tool offers this)
- **True offline capability** with automatic model management and SHA256 verification
- **Memory-efficient streaming** architecture using Iterator[bytes]
- **Consistent error handling** with categorized exit codes and helpful messages
- **Security-first design** with sanitized output and proper credential management

# Target Audience

Developers who need reliable text-to-speech in their workflows, content creators generating audio from scripts, accessibility tool developers, anyone who prefers command-line tools, and users who want both cloud and offline TTS options without vendor lock-in.