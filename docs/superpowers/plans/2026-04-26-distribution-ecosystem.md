# Distribution & Ecosystem Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add first-class shell completion helpers and packaged voice-pack metadata to `par-tts`, then update docs and remove completed ideas.

**Architecture:** Keep the existing single-command Typer CLI and add metadata-only flags that run before provider creation. Put voice-pack loading in a focused library module backed by packaged YAML data loaded via `importlib.resources`; put shell completion helper logic in a focused CLI support module that uses Click/Typer completion environment variables.

**Tech Stack:** Python 3.11+, Typer/Click, PyYAML, importlib.resources, Rich tables, pytest `CliRunner`, Hatchling package data.

---

## File Structure

- Create `par_tts/data/voice_packs.yaml`: packaged starter catalog with curated use-case packs.
- Create `par_tts/voice_packs.py`: typed loader, validation, lookup, and formatting-neutral data structures.
- Create `par_tts/cli/completions.py`: shell validation, script generation, and install instruction rendering.
- Modify `par_tts/cli/tts_cli.py`: add CLI flags and metadata-only handlers before provider creation.
- Modify `tests/test_cli_quick_wins.py`: CLI coverage for completions and voice packs.
- Modify `pyproject.toml`: ensure YAML data is included in wheel/sdist.
- Modify `README.md` and `docs/ARCHITECTURE.md`: document the new features.
- Modify `ideas.md`: remove completed Distribution & Ecosystem items.

## Task 1: Voice-Pack Metadata Module

**Files:**
- Create: `par_tts/data/voice_packs.yaml`
- Create: `par_tts/voice_packs.py`
- Test: `tests/test_cli_quick_wins.py`

- [ ] **Step 1: Write failing CLI tests**

Add tests to `tests/test_cli_quick_wins.py`:

```python
def test_list_voice_packs_does_not_create_provider(monkeypatch):
    runner = CliRunner()

    def fail_create_provider(*args: Any, **kwargs: Any) -> FakeProvider:
        raise AssertionError("voice-pack listing should not create a provider")

    monkeypatch.setattr(tts_cli, "create_provider", fail_create_provider)

    result = runner.invoke(tts_cli.app, ["--list-voice-packs"])

    assert result.exit_code == 0
    assert "Voice packs" in result.output
    assert "assistant" in result.output
    assert "alerts" in result.output


def test_show_voice_pack_prints_recommendations_without_provider(monkeypatch):
    runner = CliRunner()

    def fail_create_provider(*args: Any, **kwargs: Any) -> FakeProvider:
        raise AssertionError("voice-pack display should not create a provider")

    monkeypatch.setattr(tts_cli, "create_provider", fail_create_provider)

    result = runner.invoke(tts_cli.app, ["--show-voice-pack", "assistant"])

    assert result.exit_code == 0
    assert "assistant" in result.output
    assert "Provider" in result.output
    assert "Voice" in result.output


def test_show_unknown_voice_pack_fails_cleanly():
    runner = CliRunner()

    result = runner.invoke(tts_cli.app, ["--show-voice-pack", "missing-pack"])

    assert result.exit_code != 0
    assert "Unknown voice pack" in result.output
    assert "assistant" in result.output
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest tests/test_cli_quick_wins.py::test_list_voice_packs_does_not_create_provider tests/test_cli_quick_wins.py::test_show_voice_pack_prints_recommendations_without_provider tests/test_cli_quick_wins.py::test_show_unknown_voice_pack_fails_cleanly -v
```

Expected: fail because the CLI options do not exist yet.

- [ ] **Step 3: Add voice-pack data and loader**

Create `par_tts/data/voice_packs.yaml` with four packs: `alerts`, `assistant`, `narration`, and `storytelling`. Each pack has `description` and `voices` entries containing `provider`, `voice`, optional `model`, and `notes`.

Create `par_tts/voice_packs.py` with:

```python
from dataclasses import dataclass
from importlib import resources
from typing import Any

import yaml

from par_tts.errors import ErrorType, TTSError

VOICE_PACKS_RESOURCE = "voice_packs.yaml"

@dataclass(frozen=True)
class VoicePackRecommendation:
    provider: str
    voice: str
    model: str | None = None
    notes: str | None = None

@dataclass(frozen=True)
class VoicePack:
    name: str
    description: str
    voices: tuple[VoicePackRecommendation, ...]
```

Implement `load_voice_packs()` and `get_voice_pack(name: str)` with strict shape checks and helpful `TTSError` messages.

- [ ] **Step 4: Add CLI handlers**

In `par_tts/cli/tts_cli.py`, import the loader, add options `--list-voice-packs` and `--show-voice-pack`, include them in `text_required` exemptions, and handle them before provider creation by rendering Rich tables.

- [ ] **Step 5: Run tests and verify pass**

Run the three tests from Step 2. Expected: pass.

- [ ] **Step 6: Commit task**

```bash
git add par_tts/data/voice_packs.yaml par_tts/voice_packs.py par_tts/cli/tts_cli.py tests/test_cli_quick_wins.py
git commit -m "feat: add built-in voice packs"
```

## Task 2: Shell Completion Helpers

**Files:**
- Create: `par_tts/cli/completions.py`
- Modify: `par_tts/cli/tts_cli.py`
- Test: `tests/test_cli_quick_wins.py`

- [ ] **Step 1: Write failing CLI tests**

Add tests to `tests/test_cli_quick_wins.py`:

```python
def test_completion_script_prints_for_supported_shell_without_provider(monkeypatch):
    runner = CliRunner()

    def fail_create_provider(*args: Any, **kwargs: Any) -> FakeProvider:
        raise AssertionError("completion generation should not create a provider")

    monkeypatch.setattr(tts_cli, "create_provider", fail_create_provider)

    result = runner.invoke(tts_cli.app, ["--completion", "bash"])

    assert result.exit_code == 0
    assert "complete" in result.output.lower()
    assert "par-tts" in result.output


def test_completion_install_prints_shell_specific_instructions(monkeypatch):
    runner = CliRunner()

    def fail_create_provider(*args: Any, **kwargs: Any) -> FakeProvider:
        raise AssertionError("completion install help should not create a provider")

    monkeypatch.setattr(tts_cli, "create_provider", fail_create_provider)

    result = runner.invoke(tts_cli.app, ["--completion-install", "fish"])

    assert result.exit_code == 0
    assert "fish" in result.output.lower()
    assert "par-tts --completion fish" in result.output


def test_completion_rejects_unknown_shell():
    runner = CliRunner()

    result = runner.invoke(tts_cli.app, ["--completion", "powershell"])

    assert result.exit_code != 0
    assert "Unsupported shell" in result.output
    assert "bash" in result.output
```

- [ ] **Step 2: Run tests and verify failure**

Run:

```bash
uv run pytest tests/test_cli_quick_wins.py::test_completion_script_prints_for_supported_shell_without_provider tests/test_cli_quick_wins.py::test_completion_install_prints_shell_specific_instructions tests/test_cli_quick_wins.py::test_completion_rejects_unknown_shell -v
```

Expected: fail because the CLI options do not exist yet.

- [ ] **Step 3: Implement completion helpers**

Create `par_tts/cli/completions.py` with `SUPPORTED_SHELLS = ("bash", "zsh", "fish")`, `normalize_shell(shell: str)`, `generate_completion_script(shell: str, program_name: str = "par-tts")`, and `completion_install_instructions(shell: str)`. Generate scripts by setting `_{PROGRAM_NAME}_COMPLETE={shell}_source` and invoking `sys.executable -m par_tts.cli.tts_cli` with `subprocess.run`, or by falling back to clear manual eval instructions if direct generation is unavailable.

- [ ] **Step 4: Add CLI flags and handlers**

In `par_tts/cli/tts_cli.py`, add `--completion` and `--completion-install` options, include them in text-required exemptions, and handle them before provider creation.

- [ ] **Step 5: Run tests and verify pass**

Run the three tests from Step 2. Expected: pass.

- [ ] **Step 6: Commit task**

```bash
git add par_tts/cli/completions.py par_tts/cli/tts_cli.py tests/test_cli_quick_wins.py
git commit -m "feat: add shell completion helpers"
```

## Task 3: Packaging and Documentation

**Files:**
- Modify: `pyproject.toml`
- Modify: `README.md`
- Modify: `docs/ARCHITECTURE.md`
- Modify: `ideas.md`

- [ ] **Step 1: Write package data inclusion change**

Update `pyproject.toml` wheel and sdist include lists so `par_tts/data/**/*.yaml` is packaged.

- [ ] **Step 2: Update README**

Add docs under Installation/Usage for:

```bash
par-tts --completion bash > ~/.local/share/bash-completion/completions/par-tts
par-tts --completion zsh > ~/.zfunc/_par-tts
par-tts --completion fish > ~/.config/fish/completions/par-tts.fish
par-tts --completion-install bash
par-tts --list-voice-packs
par-tts --show-voice-pack assistant
```

- [ ] **Step 3: Update architecture docs**

Document that metadata-only operations include completion helpers and voice packs, and that voice-pack data is loaded from packaged YAML through `par_tts.voice_packs`.

- [ ] **Step 4: Remove completed ideas**

Edit `ideas.md` to remove Distribution & Ecosystem items 19 and 21. If the section becomes empty, remove the section header.

- [ ] **Step 5: Run verification**

Run:

```bash
make checkall
```

Expected: format, lint, typecheck, and tests pass.

- [ ] **Step 6: Commit task**

```bash
git add pyproject.toml README.md docs/ARCHITECTURE.md ideas.md
git commit -m "docs: document distribution ecosystem features"
```

## Task 4: Final Verification

**Files:**
- Verify only unless fixes are required.

- [ ] **Step 1: Run focused CLI smoke checks**

```bash
uv run par-tts --list-voice-packs
uv run par-tts --show-voice-pack assistant
uv run par-tts --completion-install bash
```

Expected: each command exits 0 and prints the requested metadata/help without requiring API keys.

- [ ] **Step 2: Run canonical verification**

```bash
make checkall
```

Expected: all checks pass.

- [ ] **Step 3: Commit any verifier fixes**

If Step 1 or Step 2 required fixes, commit only those fixes with:

```bash
git add <fixed files>
git commit -m "fix: polish distribution ecosystem features"
```
