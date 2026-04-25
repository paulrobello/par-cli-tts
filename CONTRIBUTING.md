# Contributing to PAR CLI TTS

Thank you for your interest in contributing to PAR CLI TTS. This guide covers everything you need to get started.

## Table of Contents

- [Development Setup](#development-setup)
- [Development Commands](#development-commands)
- [Coding Conventions](#coding-conventions)
- [Commit Format](#commit-format)
- [Pull Request Process](#pull-request-process)
- [Testing Requirements](#testing-requirements)
- [Adding a New Provider](#adding-a-new-provider)

## Development Setup

### Prerequisites

- Python 3.11 or later
- [uv](https://docs.astral.sh/uv/) package manager

### Setup Steps

1. **Clone the repository**
   ```bash
   git clone https://github.com/paulrobello/par-cli-tts.git
   cd par-cli-tts
   ```

2. **Install dependencies**
   ```bash
   uv sync
   ```

3. **Verify installation**
   ```bash
   uv run par-tts --help
   ```

4. **Create a `.env` file** for API keys (only needed for testing cloud providers)
   ```bash
   cp .env.example .env
   # Edit .env with your API keys
   ```

## Development Commands

All development commands are available via the Makefile:

```bash
# Run all checks (format, lint, typecheck) — run this before every commit
make checkall

# Individual checks
make format      # Format code with ruff
make lint        # Lint with ruff (auto-fix)
make typecheck   # Type check with pyright

# Running
make run         # Run with a test message
make app_help    # Show CLI help

# Voice and model management
make list-voices      # List available voices
make update-cache     # Update ElevenLabs voice cache
make clear-cache      # Clear cached voice data
make kokoro-download  # Download Kokoro ONNX models
make kokoro-info      # Show Kokoro model info

# Building
make package     # Build wheel distribution
make clean       # Clean build artifacts
```

## Coding Conventions

### Type Annotations

- Use type annotations for all function parameters and return values
- Prefer `str | None` over `Optional[str]`
- Use `Any` sparingly; prefer typed dicts or Protocol for provider-specific kwargs
- All new files must pass strict pyright checks

### Docstrings

- Use Google-style docstrings for all public functions, classes, and methods
- Include `Args`, `Returns`, and `Raises` sections where applicable
- Add `Example` sections for non-obvious usage

```python
def resolve_voice(self, voice_identifier: str) -> str:
    """Resolve a voice name or ID to a valid voice ID.

    Args:
        voice_identifier: Voice name or ID to resolve.

    Returns:
        Valid voice ID for the provider.

    Raises:
        ValueError: If voice cannot be resolved.
    """
```

### Import Style

- Use `from __future__ import annotations` in all new files
- Group imports: stdlib, third-party, local (separated by blank lines)
- Use `par_tts` for all internal imports (not `par_cli_tts`)

### Error Handling

- Use `TTSError` from `par_tts.errors` for library-level errors
- Reserve `sys.exit()` for the CLI layer only
- Use the `ErrorType` enum for categorized error codes

### Provider Pattern

- All providers inherit from `TTSProvider` in `par_tts/providers/base.py`
- Register new providers in the `PROVIDERS` dict in `par_tts/providers/__init__.py`
- Providers accept `api_key` as optional (offline providers set it to `None`)

## Commit Format

Use conventional commit format with a type prefix:

```
type(scope): description

[optional body]
```

**Types:**

| Type | Usage |
|------|-------|
| `feat` | New feature or provider |
| `fix` | Bug fix |
| `docs` | Documentation changes |
| `refactor` | Code restructuring without behavior change |
| `test` | Adding or updating tests |
| `chore` | Build, CI, dependency updates |
| `perf` | Performance improvements |

**Examples:**

```
feat(deepgram): add Aura-2 voice catalog
fix(voice-cache): correct expiry calculation
docs(readme): update installation instructions
refactor(cli): extract helper functions from main()
chore(deps): update openai SDK dependency
```

## Pull Request Process

### Before Submitting

1. **Run all checks**: `make checkall` must pass with zero errors
2. **Write tests**: Cover new functionality and edge cases
3. **Update documentation**: Update README, CLAUDE.md, and ARCHITECTURE.md as needed
4. **Atomic commits**: Each commit should represent one logical change

### PR Guidelines

- **Title**: Use conventional commit format (e.g., `feat(gemini): add voice instructions support`)
- **Description**: Explain what the change does, why it is needed, and how to test it
- **Scope**: Keep PRs focused on a single concern
- **Tests**: Include tests that verify the new behavior or fix
- **Documentation**: Update relevant docs in the same PR

### Review Criteria

- All CI checks pass
- Code follows project conventions (type annotations, docstrings, import style)
- New features include tests
- Documentation is updated
- No unnecessary dependencies introduced

## Testing Requirements

### Running Tests

```bash
# Run full test suite
uv run pytest

# Run with coverage
uv run pytest --cov=par_tts

# Run specific test file
uv run pytest tests/test_config.py

# Run with verbose output
uv run pytest -v
```

### Test Organization

```
tests/
├── conftest.py              # Shared fixtures
├── test_api_surface.py      # Public API surface tests
├── test_config.py           # Configuration tests
├── test_logging_decouple.py # Library/CLI separation tests
├── test_voice_cache.py      # Voice cache tests
└── test_providers/
    └── test_provider_options.py  # Provider option tests
```

### Writing Tests

- Use `pytest` fixtures for common setup
- Test both success and error paths
- Mock external API calls (use `unittest.mock` or `pytest-mock`)
- Library code tests must not import from `par_tts.cli` (enforced by `test_logging_decouple.py`)

## Adding a New Provider

1. **Create the provider file**: `par_tts/providers/new_provider.py`
2. **Inherit from `TTSProvider`**: Implement all abstract methods and properties
3. **Register in `PROVIDERS`**: Add entry in `par_tts/providers/__init__.py`
4. **Add CLI support**: Update provider kwargs and help text in `par_tts/cli/tts_cli.py`
5. **Add environment variables**: Document in README and CLAUDE.md
6. **Add tests**: Cover voice resolution, speech generation, and error handling
7. **Update documentation**: README, CLAUDE.md, and ARCHITECTURE.md
