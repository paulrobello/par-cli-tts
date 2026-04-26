"""Shell completion helpers for the par-tts CLI."""

from __future__ import annotations

import typer.completion

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


def generate_completion_script(shell: str, program_name: str = "par-tts") -> str:
    """Return a shell completion script for bash, zsh, or fish."""
    normalized_shell = normalize_shell(shell)
    completion_script = getattr(typer.completion, "get_completion_script")
    return completion_script(
        prog_name=program_name,
        complete_var=_completion_env_var(program_name),
        shell=normalized_shell,
    )


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
