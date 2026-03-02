# Refactor Audit

## Executive Summary
- Total findings: 10 (high: 3, medium: 4, low: 3)
- Files exceeding 800 lines: 0
- Files in the 500-800 line warning zone: 1 (`tts_cli.py` at 717 lines)
- Estimated total effort: M (Medium)

## Findings (ranked by impact)

### [HIGH] R-01: Monolithic main() Function - `src/tts_cli.py` (717 lines)
**Category**: God Object
**Effort**: M
**Recommendation**: Extract the 588-line `main()` function (lines 126-714) into smaller, focused functions:
- `handle_config_operations()` - config creation/dumping
- `handle_input_operations()` - stdin/file/argument text input
- `handle_list_operations()` - list providers/voices
- `handle_voice_preview()` - voice preview logic
- `handle_speech_generation()` - core TTS generation and output

This function currently handles 15+ CLI flags, config merging, input validation, voice resolution, audio generation, file management, and playback - all in one function.

---

### [HIGH] R-02: Duplicated Audio Playback Logic - `src/providers/openai.py` & `src/providers/kokoro_onnx.py`
**Category**: DRY
**Effort**: S
**Recommendation**: Extract the platform-specific audio player selection code into a shared utility function in `src/utils.py`:

```python
def play_audio_with_player(file_path: Path, volume: float = 1.0) -> None:
    """Play audio using system player with volume support."""
```

Both providers have nearly identical 25+ line blocks (openai.py:194-218, kokoro_onnx.py:196-224) that:
- Detect platform (Darwin/Windows/Linux)
- Try multiple players with volume flags (paplay, ffplay, mpg123, aplay)
- Handle fallbacks

---

### [HIGH] R-03: Missing Test Coverage - Project Root
**Category**: Test Organization
**Effort**: M
**Recommendation**: Create a `tests/` directory with:
- `tests/test_providers/` - Provider tests (mock API responses)
- `tests/test_voice_cache.py` - Cache operations
- `tests/test_config.py` - Configuration loading
- `tests/test_utils.py` - Utility functions
- `tests/conftest.py` - Shared fixtures

No tests currently exist despite ~2700 lines of code.

---

### [MEDIUM] R-04: Duplicated HTTP Client Configuration - `src/providers/elevenlabs.py` & `src/providers/openai.py`
**Category**: DRY
**Effort**: S
**Recommendation**: Create a factory function in a shared module:

```python
# src/http_client.py
def create_http_client(timeout: float = 10.0) -> httpx.Client:
    """Create HTTP client with SSL verification disabled."""
    return httpx.Client(verify=False, timeout=timeout)
```

Both providers create identical httpx clients with `verify=False` (elevenlabs.py:35, openai.py:40).

---

### [MEDIUM] R-05: Duplicate Provider-Specific Kwargs - `src/tts_cli.py` & `src/config.py`
**Category**: DRY
**Effort**: S
**Recommendation**: Consolidate provider kwargs preparation. The `TTSConfig.get_provider_kwargs()` method in `config.py` (lines 50-66) duplicates logic in `tts_cli.py` (lines 599-621). Either:
1. Use the `TTSConfig` class in the CLI instead of manual dict building, OR
2. Remove the unused `config.py` dataclasses entirely

Currently `config.py` defines dataclasses that aren't used by the CLI.

---

### [MEDIUM] R-06: Redundant Configuration Modules - `src/config.py` & `src/config_file.py`
**Category**: Module Boundary
**Effort**: M
**Recommendation**: Merge these two modules. They serve overlapping purposes:
- `config.py` (66 lines) - Defines dataclasses: `AudioSettings`, `OutputSettings`, `ProviderSettings`, `TTSConfig`
- `config_file.py` (175 lines) - Defines Pydantic models: `ConfigFile`, `ConfigManager`

The dataclasses in `config.py` appear to be unused (the CLI uses `ConfigFile` from `config_file.py`). Either:
1. Remove `config.py` entirely, OR
2. Replace Pydantic models with dataclasses in `config_file.py`

---

### [MEDIUM] R-07: Tight Coupling Between Voice Cache and ElevenLabs Provider
**Category**: Module Boundary
**Effort**: S
**Recommendation**: The `resolve_voice_identifier()` function in `voice_cache.py` (lines 330-414) takes an `ElevenLabs` client directly, creating tight coupling. Consider:
1. Making it accept a generic interface/protocol instead of the concrete client, OR
2. Moving this function into `ElevenLabsProvider` class where it naturally belongs

The import of `ElevenLabs` in `voice_cache.py` (line 16) creates a circular-ish dependency pattern.

---

### [LOW] R-08: Inline Voice ID Detection - `src/voice_cache.py` & `src/providers/elevenlabs.py`
**Category**: Missing Abstraction
**Effort**: S
**Recommendation**: The voice ID detection pattern `len(identifier) >= 20 and identifier.replace("_", "").isalnum()` appears in `voice_cache.py:349`. This could be a utility function:

```python
def looks_like_voice_id(identifier: str, min_length: int = 20) -> bool:
    """Check if identifier looks like a voice ID rather than a name."""
```

---

### [LOW] R-09: Scattered Default Voice Definitions - Multiple Files
**Category**: DRY
**Effort**: S
**Recommendation**: Default voices are defined in multiple places:
- `tts_cli.py:32-34` - CLI defaults
- `elevenlabs.py:57` - Provider default
- `openai.py:61` - Provider default
- `kokoro_onnx.py:79` - Provider default

Consider a central `defaults.py` or using provider class properties consistently.

---

### [LOW] R-10: Console Instance Duplication - Multiple Files
**Category**: DRY
**Effort**: S
**Recommendation**: Each module creates its own `Console()` instance:
- `tts_cli.py:27`
- `voice_cache.py:19`
- `elevenlabs.py:19`
- `openai.py:14`
- `errors.py:9`
- `config_file.py:11`
- `kokoro_cli.py:13`
- `model_downloader.py:12`

Consider a shared console in `src/console.py` for consistent output handling.

---

## Dependency Graph

Findings that can be worked on in parallel (no shared state or sequential dependency):

**Wave 1** (no prerequisites - independent fixes):
- R-02: Extract audio playback utility
- R-03: Create test directory structure
- R-04: Create HTTP client factory
- R-08: Create voice ID detection utility
- R-09: Create defaults module
- R-10: Create shared console module

**Wave 2** (after Wave 1):
- R-05: Consolidate provider kwargs (can use R-09 defaults)
- R-06: Merge config modules (independent but benefits from clean slate)
- R-07: Decouple voice cache from provider (independent refactoring)

**Wave 3** (after Wave 2):
- R-01: Refactor main() function (benefits from all utilities being in place)

## Quick Wins (High Impact, Low Effort)

| ID | Finding | Effort | Impact |
|----|---------|--------|--------|
| R-02 | Duplicated audio playback logic | S | HIGH |
| R-04 | Duplicated HTTP client config | S | MEDIUM |
| R-08 | Voice ID detection utility | S | LOW |
| R-09 | Centralized defaults | S | LOW |
| R-10 | Shared console | S | LOW |

## Recommended Action Order

1. **Start with Wave 1 quick wins** - These are simple extractions that reduce duplication immediately
2. **Address R-03 (tests)** - Critical for maintaining quality during refactoring
3. **Tackle R-01 (main function)** - The biggest impact on maintainability
4. **Clean up config modules (R-05, R-06)** - Consolidate configuration handling

---

## Appendix: Files by Line Count (descending)

| File | Lines | Status |
|------|-------|--------|
| src/tts_cli.py | 717 | WARNING |
| src/voice_cache.py | 414 | OK |
| src/providers/kokoro_onnx.py | 228 | OK |
| src/model_downloader.py | 224 | OK |
| src/providers/openai.py | 221 | OK |
| src/config_file.py | 175 | OK |
| src/providers/elevenlabs.py | 174 | OK |
| src/errors.py | 150 | OK |
| src/providers/base.py | 138 | OK |
| src/kokoro_cli.py | 113 | OK |
| src/utils.py | 101 | OK |
| src/config.py | 66 | OK |
| src/providers/__init__.py | 14 | OK |
| src/__init__.py | 3 | OK |
| **Total** | **~2738** | |

---

## Detailed Code Locations

### R-01: Main function breakdown
- Config handling: lines 317-346
- Input handling: lines 351-386
- List operations: lines 388-445
- Voice preview: lines 447-494
- Config dump: lines 502-546
- Audio generation: lines 596-713

### R-02: Duplicated playback code
- `src/providers/openai.py:194-218` (24 lines)
- `src/providers/kokoro_onnx.py:196-224` (28 lines)

### R-04: Duplicated HTTP client
- `src/providers/elevenlabs.py:35`
- `src/providers/openai.py:40`
