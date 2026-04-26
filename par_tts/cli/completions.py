"""Shell completion helpers for the par-tts CLI."""

from __future__ import annotations

import os
import subprocess
import sys

from par_tts.errors import ErrorType, TTSError

SUPPORTED_SHELLS = ("bash", "zsh", "fish")


def normalize_shell(shell: str) -> str:
    """Normalize and validate a requested shell name."""
    normalized = shell.strip().lower()
    if normalized not in SUPPORTED_SHELLS:
        supported = ", ".join(SUPPORTED_SHELLS)
        raise TTSError(
            f"Unsupported shell '{shell}'. Supported shells: {supported}",
            ErrorType.INVALID_INPUT,
        )
    return normalized


def _completion_env_var(program_name: str) -> str:
    normalized_program = program_name.replace("-", "_").upper()
    return f"_{normalized_program}_COMPLETE"


def _fallback_completion_script(shell: str, program_name: str) -> str:
    env_var = _completion_env_var(program_name)
    if shell == "bash":
        return (
            f"# bash completion for {program_name}\n"
            f"# Regenerate with: {program_name} --completion bash\n"
            f"eval \"$({env_var}=bash_source {program_name})\"\n"
        )
    if shell == "zsh":
        return (
            f"# zsh completion for {program_name}\n"
            f"# Regenerate with: {program_name} --completion zsh\n"
            f"eval \"$({env_var}=zsh_source {program_name})\"\n"
        )
    return (
        f"# fish completion for {program_name}\n"
        f"# Regenerate with: {program_name} --completion fish\n"
        f"{env_var}=fish_source {program_name} | source\n"
    )


def generate_completion_script(shell: str, program_name: str = "par-tts") -> str:
    """Return a shell completion script for bash, zsh, or fish.

    Typer/Click expose completion scripts through a standard environment
    variable. We try that mechanism first, then fall back to a deterministic
    delegating snippet so this command remains useful in constrained contexts.
    """
    normalized_shell = normalize_shell(shell)
    env = os.environ.copy()
    env[_completion_env_var(program_name)] = f"{normalized_shell}_source"
    try:
        result = subprocess.run(
            [sys.executable, "-m", "par_tts.cli.tts_cli"],
            check=False,
            capture_output=True,
            env=env,
            text=True,
            timeout=10,
        )
    except (OSError, subprocess.SubprocessError, TimeoutError):
        return _fallback_completion_script(normalized_shell, program_name)

    if result.returncode == 0 and result.stdout.strip():
        return result.stdout
    return _fallback_completion_script(normalized_shell, program_name)


def completion_install_instructions(shell: str) -> str:
    """Return concrete installation instructions for a supported shell."""
    normalized_shell = normalize_shell(shell)
    if normalized_shell == "bash":
        return "\n".join(
            [
                "Bash completion for par-tts:",
                "  mkdir -p ~/.local/share/bash-completion/completions",
                "  par-tts --completion bash > ~/.local/share/bash-completion/completions/par-tts",
                "  # Restart your shell or source the generated file.",
            ]
        )
    if normalized_shell == "zsh":
        return "\n".join(
            [
                "Zsh completion for par-tts:",
                "  mkdir -p ~/.zfunc",
                "  par-tts --completion zsh > ~/.zfunc/_par-tts",
                "  # Add this to ~/.zshrc if needed: fpath=(~/.zfunc $fpath); autoload -Uz compinit; compinit",
            ]
        )
    return "\n".join(
        [
            "Fish completion for par-tts:",
            "  mkdir -p ~/.config/fish/completions",
            "  par-tts --completion fish > ~/.config/fish/completions/par-tts.fish",
            "  # Fish will load the completion automatically for new shells.",
        ]
    )
