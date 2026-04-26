#!/usr/bin/env python
"""
Command line tool for text-to-speech using multiple TTS providers.

This module provides a CLI interface for converting text to speech using
various TTS providers (ElevenLabs, OpenAI, etc). It supports configurable
voices, multiple providers, and various output options.
"""

import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, TextIO

import typer
from dotenv import load_dotenv
from rich.pretty import Pretty
from rich.table import Table

from par_tts.audio_processing import AudioProcessingOptions, concat_audio_files, postprocess_audio_file
from par_tts.cli.completions import completion_install_instructions, generate_completion_script
from par_tts.cli.config_file import ConfigManager
from par_tts.cli.console import console
from par_tts.defaults import DEFAULT_PROVIDER, get_default_voice
from par_tts.errors import ErrorType, TTSError, handle_error, set_debug_mode, validate_api_key, validate_file_path
from par_tts.logging_config import configure_logging
from par_tts.providers import PROVIDERS, TTSProvider, get_plugin_diagnostics, get_provider_plugin, get_provider_plugins
from par_tts.text_processing import TextSegment, build_text_segments
from par_tts.voice_packs import VoicePack, get_voice_pack, load_voice_packs
from par_tts.workflow import (
    BatchRecord,
    NotificationDefaults,
    build_timestamp_entries,
    changed_watch_inputs,
    discover_watch_inputs,
    output_path_for_record,
    parse_batch_records,
    parse_template_vars,
    render_template,
    split_caption_segments,
    watch_snapshot,
    write_timestamp_export,
)

app = typer.Typer(help="Text-to-speech command line tool with multiple provider support")

DEFAULT_MODELS: dict[str, str] = {
    "elevenlabs": "eleven_multilingual_v2",
    "openai": "gpt-4o-mini-tts",
    "kokoro-onnx": "kokoro-v1.0",
    "deepgram": "aura-2-thalia-en",
    "gemini": "gemini-2.5-flash-preview-tts",
}

# Approximate per-million-character rates for quick estimates. Cloud provider
# billing changes over time, so display these as rough planning numbers only.
COST_PER_MILLION_CHARS: dict[str, dict[str, float]] = {
    "openai": {"default": 15.0, "tts-1": 15.0, "tts-1-hd": 30.0, "gpt-4o-mini-tts": 15.0},
    "elevenlabs": {"default": 30.0},
    "deepgram": {"default": 30.0},
    "gemini": {"default": 0.50},
    "kokoro-onnx": {"default": 0.0, "kokoro-v1.0": 0.0},
}


@dataclass
class CostEstimate:
    """Static, approximate synthesis cost estimate."""

    provider: str
    model: str
    characters: int
    cost_usd: float | None
    rate_per_million: float | None


@dataclass
class SpeechGenerationResult:
    """Summary of one speech generation operation."""

    provider: str
    model: str
    voice: str
    text_length: int
    output_path: Path | None
    output_bytes: int | None
    played: bool
    elapsed_seconds: float


@dataclass
class VoiceBenchmarkResult:
    """Objective result from one benchmark synthesis run."""

    provider: str
    model: str
    voice: str
    run_number: int
    text_length: int
    output_bytes: int | None
    elapsed_seconds: float
    cost_usd: float | None


def _run_cli() -> None:
    """Invoke the Typer app, catching TTSError and translating to sys.exit().

    Library code raises :class:`TTSError` instead of calling ``sys.exit()`` so
    that programmatic users can handle errors gracefully.  This wrapper is the
    CLI boundary: it catches those exceptions, prints a user-friendly message,
    and exits with the appropriate code.
    """
    try:
        app()
    except TTSError as exc:
        console.print(f"[red]{exc.error_type.display_name}:[/red] {exc.message}")
        sys.exit(exc.error_type.exit_code)


def estimate_synthesis_cost(provider: str, model: str | None, text: str) -> CostEstimate:
    """Estimate synthesis cost from static provider/model pricing.

    Args:
        provider: Provider name.
        model: Requested model, or None to use provider default.
        text: Input text.

    Returns:
        Approximate cost estimate.
    """
    resolved_model = model or DEFAULT_MODELS.get(provider, "default")
    provider_rates = COST_PER_MILLION_CHARS.get(provider, {})
    rate = provider_rates.get(resolved_model, provider_rates.get("default"))
    characters = len(text)
    cost = None if rate is None else (characters / 1_000_000) * rate
    return CostEstimate(
        provider=provider,
        model=resolved_model,
        characters=characters,
        cost_usd=cost,
        rate_per_million=rate,
    )


def print_cost_estimate(estimate: CostEstimate) -> None:
    """Print a cost estimate."""
    console.print("[bold cyan]Cost estimate:[/bold cyan]")
    console.print(f"  provider: {estimate.provider}")
    console.print(f"  model: {estimate.model}")
    console.print(f"  characters: {estimate.characters}")
    if estimate.cost_usd is None or estimate.rate_per_million is None:
        console.print("  estimated_cost: unavailable")
    else:
        console.print(f"  rate: ${estimate.rate_per_million:.2f} per 1M characters")
        console.print(f"  estimated_cost: ${estimate.cost_usd:.6f}")
    console.print("[dim]Estimate is approximate; check provider pricing for billing decisions.[/dim]")


def build_operation_plan(
    *,
    provider: str,
    voice: str | None,
    model: str | None,
    text: str | None,
    output: Path | None,
    play_audio: bool,
    keep_temp: bool,
    temp_dir: Path | None,
    volume: float,
    stability: float,
    similarity_boost: float,
    speed: float,
    response_format: str,
    lang: str,
    instructions: str | None,
    retry_attempts: int = 0,
    retry_backoff: float = 0.0,
) -> dict[str, Any]:
    """Build an inspectable plan for dry-run output."""
    resolved_voice = voice or get_default_voice(provider)
    return {
        "provider": provider,
        "model": model or DEFAULT_MODELS.get(provider, "default"),
        "voice": resolved_voice,
        "text_length": len(text or ""),
        "output": str(output) if output else None,
        "play_audio": play_audio,
        "keep_temp": keep_temp,
        "temp_dir": str(temp_dir) if temp_dir else None,
        "volume": volume,
        "provider_options": get_provider_kwargs(
            provider=provider,
            stability=stability,
            similarity_boost=similarity_boost,
            speed=speed,
            response_format=response_format,
            lang=lang,
            instructions=instructions,
        ),
        "retry_policy": {"retry_attempts": retry_attempts, "retry_backoff": retry_backoff},
    }


def print_dry_run_plan(plan: dict[str, Any]) -> None:
    """Print dry-run operation plan."""
    console.print("[bold cyan]Dry run — no speech will be generated.[/bold cyan]")
    console.print(Pretty(plan))


def _voice_search_text(voice: Any) -> str:
    labels = " ".join(voice.labels or [])
    return f"{voice.id} {voice.name} {labels} {voice.category or ''}".lower()


def _fuzzy_score(query: str, candidate: str) -> int:
    """Return a simple fuzzy score; lower means no match."""
    query = query.lower().strip()
    if not query:
        return 0
    if query in candidate:
        return 100 + len(query)

    position = -1
    score = 0
    for char in query:
        next_position = candidate.find(char, position + 1)
        if next_position == -1:
            return 0
        score += 5 if next_position == position + 1 else 1
        position = next_position
    return score


def search_voices(voices: Iterable[Any], query: str) -> list[Any]:
    """Search provider voices by id, name, labels, and category."""
    scored = [(_fuzzy_score(query, _voice_search_text(voice)), voice) for voice in voices]
    return [voice for score, voice in sorted(scored, key=lambda item: item[0], reverse=True) if score > 0]


def handle_voice_search(tts_provider: TTSProvider, query: str) -> None:
    """Display voices matching a search query."""
    matches = search_voices(tts_provider.list_voices(), query)
    console.print(f"[bold green]Voice search results for '{query}' on {tts_provider.name}:[/bold green]")
    if not matches:
        console.print("[yellow]No voices matched.[/yellow]")
        return
    for v in matches:
        labels_str = ", ".join(v.labels) if v.labels else "No labels"
        console.print(f"  [yellow]{v.id}[/yellow]: [white]{v.name}[/white] - {labels_str}")


def handle_doctor() -> None:
    """Run offline diagnostics and print a concise report."""
    from par_tts.diagnostics import collect_diagnostics

    console.print("[bold cyan]PAR TTS Doctor[/bold cyan]")
    for section, checks in collect_diagnostics().items():
        table = Table(title=section)
        table.add_column("Check")
        table.add_column("Status")
        table.add_column("Details")
        for check in checks:
            status = "[green]ok[/green]" if check.ok else "[yellow]warn[/yellow]"
            table.add_row(check.name, status, check.detail)
        console.print(table)


def read_clipboard_text() -> str:
    """Read text from the system clipboard using platform clipboard tools."""
    commands: list[list[str]] = []
    if sys.platform == "darwin" and shutil.which("pbpaste"):
        commands.append(["pbpaste"])
    elif sys.platform.startswith("win"):
        commands.append(["powershell", "-NoProfile", "-Command", "Get-Clipboard"])
    else:
        for command in (
            ["wl-paste", "--no-newline"],
            ["xclip", "-selection", "clipboard", "-o"],
            ["xsel", "--clipboard", "--output"],
        ):
            if shutil.which(command[0]):
                commands.append(command)

    for command in commands:
        try:
            result = subprocess.run(command, check=True, capture_output=True, text=True, timeout=5)
        except (OSError, subprocess.SubprocessError):
            continue
        if result.stdout:
            return result.stdout

    handle_error("Clipboard is empty or no supported clipboard tool is available", ErrorType.INVALID_INPUT)


def iter_stdin_chunks(stdin: TextIO) -> Iterable[str]:
    """Yield non-empty stripped lines from stdin."""
    for line in stdin:
        chunk = line.strip()
        if chunk:
            yield chunk


def print_generation_summary(result: SpeechGenerationResult) -> None:
    """Print a compact post-generation summary."""
    output = str(result.output_path) if result.output_path else "temporary file cleaned up"
    size = f", {result.output_bytes} bytes" if result.output_bytes is not None else ""
    console.print(
        "[bold cyan]Summary:[/bold cyan] "
        f"provider={result.provider}, model={result.model}, voice={result.voice}, "
        f"{result.text_length} chars, output={output}{size}, "
        f"played={result.played}, elapsed={result.elapsed_seconds:.2f}s"
    )


def _audio_size(audio_data: bytes | Iterator[bytes]) -> int:
    """Return byte size for bytes or streaming audio data."""
    if isinstance(audio_data, bytes):
        return len(audio_data)
    return sum(len(chunk) for chunk in audio_data)


def run_provider_benchmark(
    *,
    tts_provider: TTSProvider,
    provider: str,
    text: str,
    voice: str,
    model: str | None,
    repeat_count: int,
    stability: float,
    similarity_boost: float,
    speed: float,
    response_format: str,
    lang: str,
    instructions: str | None,
) -> list[VoiceBenchmarkResult]:
    """Run objective benchmark synthesis for one provider."""
    resolved_model = model or DEFAULT_MODELS.get(provider, tts_provider.default_model)
    provider_kwargs = get_provider_kwargs(
        provider=provider,
        stability=stability,
        similarity_boost=similarity_boost,
        speed=speed,
        response_format=response_format,
        lang=lang,
        instructions=instructions,
    )
    results: list[VoiceBenchmarkResult] = []
    for run_number in range(1, repeat_count + 1):
        start_time = time.perf_counter()
        audio_data = tts_provider.generate_speech(text=text, voice=voice, model=model, **provider_kwargs)
        output_bytes = _audio_size(audio_data)
        elapsed_seconds = time.perf_counter() - start_time
        cost_estimate = estimate_synthesis_cost(provider, resolved_model, text)
        results.append(
            VoiceBenchmarkResult(
                provider=provider,
                model=resolved_model,
                voice=voice,
                run_number=run_number,
                text_length=len(text),
                output_bytes=output_bytes,
                elapsed_seconds=elapsed_seconds,
                cost_usd=cost_estimate.cost_usd,
            )
        )
    return results


def print_voice_benchmark(results: list[VoiceBenchmarkResult]) -> None:
    """Print benchmark results as a table."""
    console.print("[bold cyan]Voice benchmark:[/bold cyan]")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Provider", no_wrap=True)
    table.add_column("Run", justify="right")
    table.add_column("Model")
    table.add_column("Voice")
    table.add_column("Chars", justify="right")
    table.add_column("Bytes", justify="right")
    table.add_column("Elapsed", justify="right")
    table.add_column("Cost", justify="right")
    for result in results:
        cost = "n/a" if result.cost_usd is None else f"${result.cost_usd:.6f}"
        output_bytes = "n/a" if result.output_bytes is None else str(result.output_bytes)
        table.add_row(
            result.provider,
            str(result.run_number),
            result.model,
            result.voice,
            str(result.text_length),
            output_bytes,
            f"{result.elapsed_seconds:.3f}s",
            cost,
        )
    console.print(table)


def parse_pronunciation_options(values: list[str] | None) -> dict[str, str]:
    """Parse KEY=VALUE pronunciation CLI entries."""
    pronunciations: dict[str, str] = {}
    for value in values or []:
        if "=" not in value:
            handle_error(f"Invalid pronunciation '{value}'. Expected WORD=spoken form", ErrorType.INVALID_INPUT)
        key, replacement = value.split("=", 1)
        key = key.strip()
        replacement = replacement.strip()
        if not key or not replacement:
            handle_error(f"Invalid pronunciation '{value}'. Expected WORD=spoken form", ErrorType.INVALID_INPUT)
        pronunciations[key] = replacement
    return pronunciations


def load_pronunciation_file(path: Path | None) -> dict[str, str]:
    """Load pronunciation replacements from a YAML mapping file."""
    if path is None:
        return {}
    import yaml

    expanded = Path(path).expanduser().resolve()
    validate_file_path(str(expanded), must_exist=True)
    _validate_file_read_safety(expanded)
    with open(expanded, encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    if not isinstance(data, dict):
        handle_error("Pronunciation file must contain a YAML mapping", ErrorType.CONFIG_ERROR)
    return {str(key): str(value) for key, value in data.items()}


def merge_pronunciations(*sources: dict[str, str] | None) -> dict[str, str]:
    """Merge pronunciation dictionaries, with later sources taking precedence."""
    merged: dict[str, str] = {}
    for source in sources:
        if source:
            merged.update(source)
    return merged


def get_api_key(provider: str, config_file: Any = None) -> str | None:
    """
    Get API key for the specified provider from config file or environment.

    Args:
        provider: Provider name.
        config_file: Optional config file with API keys.

    Returns:
        API key string or None for providers that don't need one.

    Raises:
        TTSError: If API key is not found anywhere.
    """
    try:
        plugin = get_provider_plugin(provider)
    except ValueError as e:
        handle_error(str(e), ErrorType.INVALID_PROVIDER, exception=e)

    if not plugin.requires_api_key:
        return None

    # Built-in config field names are retained for backward compatibility.
    config_field_map: dict[str, str] = {
        "elevenlabs": "elevenlabs_api_key",
        "openai": "openai_api_key",
        "deepgram": "deepgram_api_key",
        "gemini": "gemini_api_key",
    }
    config_field = config_field_map.get(provider)
    if config_file and config_field:
        api_key = getattr(config_file, config_field, None)
        if api_key:
            return api_key

    for env_var in plugin.api_key_env_vars:
        api_key = os.getenv(env_var)
        if api_key:
            return api_key

    if plugin.api_key_env_vars:
        primary = plugin.api_key_env_vars[0]
        alt = f" (also accepts {', '.join(plugin.api_key_env_vars[1:])})" if len(plugin.api_key_env_vars) > 1 else ""
        handle_error(
            f"{primary} not found. Please set {primary}{alt} in your config file or environment",
            ErrorType.MISSING_API_KEY,
        )

    handle_error(
        f"Provider '{provider}' requires an API key but does not declare api_key_env_vars",
        ErrorType.MISSING_API_KEY,
    )


def create_provider(provider_name: str, config_file: Any = None, **kwargs: Any) -> TTSProvider:
    """
    Create a TTS provider instance.

    Args:
        provider_name: Name of the provider.
        config_file: Optional config file with API keys.
        **kwargs: Additional provider configuration.

    Returns:
        Initialized TTS provider.

    Raises:
        TTSError: If provider is not found or cannot be initialized.
    """
    try:
        plugin = get_provider_plugin(provider_name)
    except ValueError as e:
        handle_error(str(e), ErrorType.INVALID_PROVIDER, exception=e)

    api_key = get_api_key(provider_name, config_file)
    if plugin.requires_api_key:
        validate_api_key(api_key, provider_name)
    provider_class = plugin.provider_class

    try:
        if plugin.requires_api_key:
            return provider_class(api_key, **kwargs)
        return provider_class(**kwargs)
    except Exception as e:
        handle_error(f"Failed to initialize {provider_name} provider", ErrorType.PROVIDER_ERROR, exception=e)


def get_provider_kwargs(
    provider: str,
    stability: float = 0.5,
    similarity_boost: float = 0.5,
    speed: float = 1.0,
    response_format: str = "mp3",
    lang: str = "en-us",
    instructions: str | None = None,
) -> dict[str, Any]:
    """Build provider-specific keyword arguments.

    Uses each provider's ``PROVIDER_KWARGS`` declaration to select only the
    keys that provider understands, avoiding if/elif chains.

    Args:
        provider: Provider name.
        stability: Voice stability for ElevenLabs.
        similarity_boost: Voice similarity boost for ElevenLabs.
        speed: Speech speed for OpenAI/Kokoro.
        response_format: Audio format for OpenAI.
        lang: Language code for Kokoro ONNX.
        instructions: Voice instructions for OpenAI gpt-4o-mini-tts.

    Returns:
        Dictionary of provider-specific kwargs.
    """
    all_options: dict[str, Any] = {
        "stability": stability,
        "similarity_boost": similarity_boost,
        "speed": speed,
        "response_format": response_format,
        "lang": lang,
        "instructions": instructions,
    }

    # Look up the provider class and filter to only the keys it declares
    provider_class = PROVIDERS.get(provider)
    if provider_class and provider_class.PROVIDER_KWARGS:
        return {k: v for k, v in all_options.items() if k in provider_class.PROVIDER_KWARGS}

    return {}


def handle_config_operations(create_config: bool, config_manager: ConfigManager, force: bool = False) -> bool:
    """Handle configuration-related operations.

    Args:
        create_config: Whether to create a sample config file.
        config_manager: Config manager instance.
        force: If True, overwrite an existing config without prompting.

    Returns:
        True if operation was handled and main should return, False otherwise.
    """
    if create_config:
        config_manager.create_sample_config(force=force)
        return True
    return False


def _validate_file_read_safety(file_path: Path) -> None:
    """Validate that a file path is safe to read as text input.

    Blocks reading of files outside the user's home directory and known safe
    locations to prevent accidental disclosure of sensitive system files.

    Args:
        file_path: Resolved (absolute) file path to validate.

    Raises:
        TTSError: If the path points to a sensitive or disallowed location.
    """
    # Allowed base directories (resolved, absolute)
    home = Path.home().resolve()
    allowed_prefixes: list[Path] = [
        home,
        Path(tempfile.gettempdir()).resolve(),
    ]

    # On macOS, also allow /Users which home is already under
    # Check if the file is under any allowed prefix
    if not any(_is_relative_to(file_path, prefix) for prefix in allowed_prefixes):
        handle_error(
            f"File '{file_path}' is outside allowed directories. "
            "Only files under your home directory or temp directory can be read.",
            ErrorType.INVALID_INPUT,
        )

    # Block specific sensitive filename patterns regardless of location
    sensitive_names = {
        ".env",
        ".env.local",
        ".env.production",
        ".htpasswd",
        ".ssh",
        "id_rsa",
        "id_ed25519",
        "id_ecdsa",
    }
    if file_path.name in sensitive_names:
        handle_error(
            f"File '{file_path.name}' appears to contain sensitive data and cannot be used as text input.",
            ErrorType.INVALID_INPUT,
        )


def _is_relative_to(path: Path, parent: Path) -> bool:
    """Check if *path* is inside *parent* (Python 3.9 has Path.is_relative_to).

    Args:
        path: The path to check.
        parent: The parent directory.

    Returns:
        True if path is relative to parent.
    """
    try:
        path.relative_to(parent)
        return True
    except ValueError:
        return False


def handle_input_operations(
    text: str | None,
    text_required: bool,
    from_clipboard: bool = False,
) -> str | None:
    """Handle text input from various sources.

    Args:
        text: Input text argument.
        text_required: Whether text is required for the operation.

    Returns:
        Processed text or None if not applicable.

    Raises:
        TTSError: If text is required but not provided.
    """
    if from_clipboard:
        if text is not None:
            handle_error("Use either TEXT or --from-clipboard, not both", ErrorType.INVALID_INPUT)
        text = read_clipboard_text()
        if not text:
            handle_error("Clipboard is empty", ErrorType.INVALID_INPUT)
        return text

    if text_required and text is None:
        # Check if stdin has data
        if sys.stdin.isatty():
            # No piped input, show error
            handle_error(
                "TEXT argument is required. Use --help for more information. "
                "You can also pipe text: echo 'text' | par-tts",
                ErrorType.INVALID_INPUT,
            )
        else:
            # Read from stdin automatically
            text = sys.stdin.read()
            if not text:
                handle_error("No input received from stdin", ErrorType.INVALID_INPUT)

    # Handle different text input sources
    if text and text == "-":
        # Read from stdin
        text = sys.stdin.read()
        if not text:
            handle_error("No input received from stdin", ErrorType.INVALID_INPUT)
    elif text and text.startswith("@"):
        # Read from file -- resolve and validate path to prevent traversal
        file_path = Path(text[1:]).resolve()
        validate_file_path(str(file_path), must_exist=True)

        # Block access to sensitive system files
        _validate_file_read_safety(file_path)
        try:
            with open(file_path, encoding="utf-8") as f:
                text = f.read()
            if not text:
                handle_error(f"File '{file_path}' is empty", ErrorType.INVALID_INPUT)
        except Exception as e:
            handle_error(f"Failed to read file '{file_path}'", ErrorType.FILE_NOT_FOUND, exception=e)

    return text


def handle_list_providers() -> None:
    """Display available TTS providers."""
    console.print("[bold green]Available TTS Providers:[/bold green]")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Provider")
    table.add_column("Description")
    table.add_column("Default Model")

    for name in PROVIDERS:
        try:
            p = create_provider(name)
            table.add_row(name, p.name, p.default_model)
        except Exception:
            table.add_row(name, "Configuration needed", "N/A")

    console.print(table)


def _yes_no(value: bool) -> str:
    """Render boolean capability values compactly."""
    return "yes" if value else "no"


def handle_capabilities() -> None:
    """Display provider capabilities from plugin metadata."""
    console.print("[bold green]Provider Capabilities:[/bold green]")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Provider", no_wrap=True)
    table.add_column("Source", no_wrap=True)
    table.add_column("Formats")
    table.add_column("Speed", no_wrap=True)
    table.add_column("Streaming", no_wrap=True)
    table.add_column("Voice Controls", no_wrap=True)
    table.add_column("API Key", no_wrap=True)
    table.add_column("Default Model")

    for name, plugin in sorted(get_provider_plugins().items()):
        capabilities = plugin.capabilities
        table.add_row(
            name,
            plugin.source,
            ", ".join(capabilities.formats) or "unknown",
            _yes_no(capabilities.supports_speed),
            _yes_no(capabilities.supports_streaming),
            _yes_no(capabilities.supports_voice_controls),
            "required" if plugin.requires_api_key else "not required",
            plugin.default_model,
        )

    console.print(table)
    diagnostics = get_plugin_diagnostics()
    if diagnostics:
        console.print("[yellow]Plugin diagnostics:[/yellow]")
        for diagnostic in diagnostics:
            console.print(f"  - {diagnostic}")


def handle_list_voice_packs() -> None:
    """Display bundled voice-pack metadata without provider initialization."""
    voice_packs = load_voice_packs()
    console.print("[bold green]Voice packs:[/bold green]")
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Pack", no_wrap=True)
    table.add_column("Description")
    table.add_column("Recommendations")

    for name, voice_pack in sorted(voice_packs.items()):
        recommendations = ", ".join(
            f"{recommendation.provider}/{recommendation.voice}" for recommendation in voice_pack.recommendations
        )
        table.add_row(name, voice_pack.description, recommendations)

    console.print(table)


def handle_show_voice_pack(name: str) -> None:
    """Display recommendations for one bundled voice pack."""
    voice_pack = get_voice_pack(name)
    console.print(f"[bold green]Voice pack: {voice_pack.name}[/bold green]")
    console.print(voice_pack.description)
    console.print(_build_voice_pack_table(voice_pack))


def handle_completion(shell: str) -> None:
    """Print a shell completion script without provider initialization."""
    sys.stdout.write(generate_completion_script(shell))


def handle_completion_install(shell: str) -> None:
    """Print shell-specific completion installation instructions."""
    console.print(completion_install_instructions(shell))


def _build_voice_pack_table(voice_pack: VoicePack) -> Table:
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Provider", no_wrap=True)
    table.add_column("Voice", no_wrap=True)
    table.add_column("Model")
    table.add_column("Notes")

    for recommendation in voice_pack.recommendations:
        table.add_row(
            recommendation.provider,
            recommendation.voice,
            recommendation.model or "default",
            recommendation.notes or "",
        )

    return table


def handle_list_voices(tts_provider: TTSProvider) -> None:
    """Display available voices for a provider.

    Args:
        tts_provider: TTS provider instance.
    """
    console.print(f"[bold green]Available Voices for {tts_provider.name}:[/bold green]")
    try:
        voices = tts_provider.list_voices()
        for v in voices:
            labels_str = ", ".join(v.labels) if v.labels else "No labels"
            console.print(f"  [yellow]{v.id}[/yellow]: [white]{v.name}[/white] - {labels_str}")
    except Exception as e:
        handle_error("Failed to fetch available voices", ErrorType.PROVIDER_ERROR, exception=e)


def handle_voice_preview(
    preview_voice: str,
    tts_provider: TTSProvider,
    provider: str,
    model: str | None,
    volume: float,
) -> None:
    """Preview a voice with sample text.

    Args:
        preview_voice: Voice name or ID to preview.
        tts_provider: TTS provider instance.
        provider: Provider name.
        model: Model to use for generation.
        volume: Playback volume.
    """
    console.print(f"[bold cyan]Previewing voice: {preview_voice}[/bold cyan]")
    sample_text = "Hello! This is a preview of the voice you selected. The quick brown fox jumps over the lazy dog."

    try:
        # Resolve voice
        resolved_voice = tts_provider.resolve_voice(preview_voice)
        console.print(f"[dim]Voice resolved to: {resolved_voice}[/dim]")

        # Check for cached sample first (ElevenLabs only)
        audio_data = None
        if provider == "elevenlabs":
            from par_tts.voice_cache import VoiceCache

            cache = VoiceCache("par-tts-elevenlabs")
            cached_sample = cache.get_voice_sample(resolved_voice)
            if cached_sample:
                cached_text, audio_data = cached_sample
                if cached_text == sample_text:
                    console.print("[dim]Using cached voice sample[/dim]")
                else:
                    audio_data = None  # Different sample text, regenerate

        # Generate preview speech if not cached
        if audio_data is None:
            console.print("[cyan]Generating preview...[/cyan]")
            audio_data = tts_provider.generate_speech(
                text=sample_text,
                voice=resolved_voice,
                model=model,
            )

            # Cache the sample for future use (ElevenLabs only)
            if provider == "elevenlabs" and isinstance(audio_data, bytes):
                from par_tts.voice_cache import VoiceCache

                cache = VoiceCache("par-tts-elevenlabs")
                cache.cache_voice_sample(resolved_voice, sample_text, audio_data)

        # Play the preview
        console.print("[cyan]Playing preview...[/cyan]")
        tts_provider.play_audio(audio_data, volume=volume)

        console.print("[green]Preview complete![/green]")
    except Exception as e:
        handle_error("Failed to preview voice", ErrorType.PROVIDER_ERROR, exception=e)


def handle_dump_config(
    provider: str,
    voice: str,
    model: str | None,
    output: Path | None,
    play_audio: bool,
    keep_temp: bool,
    temp_dir: Path | None,
    stability: float,
    similarity_boost: float,
    speed: float,
    response_format: str,
    lang: str,
    instructions: str | None,
    structured_logs: bool,
    log_level: str,
    retry_attempts: int,
    retry_backoff: float,
    config_file: Any,
    config_manager: ConfigManager,
    tts_provider: TTSProvider,
) -> None:
    """Dump current configuration.

    Args:
        provider: Provider name.
        voice: Voice ID.
        model: Model name.
        output: Output file path.
        play_audio: Whether to play audio.
        keep_temp: Whether to keep temp files.
        temp_dir: Temp directory path.
        stability: ElevenLabs stability.
        similarity_boost: ElevenLabs similarity boost.
        speed: Speech speed.
        response_format: Audio format.
        lang: Language code.
        instructions: Voice instructions for OpenAI.
        config_file: Loaded config file.
        config_manager: Config manager instance.
        tts_provider: TTS provider instance.
    """
    config: dict[str, Any] = {
        "provider": provider,
        "voice": voice,
        "model": model or tts_provider.default_model,
        "output": str(output) if output else None,
        "play_audio": play_audio,
        "keep_temp": keep_temp,
        "temp_dir": str(temp_dir) if temp_dir else None,
        "structured_logs": structured_logs,
        "log_level": log_level,
        "retry_attempts": retry_attempts,
        "retry_backoff": retry_backoff,
    }

    # Add provider-specific config using PROVIDER_KWARGS
    all_options: dict[str, Any] = {
        "stability": stability,
        "similarity_boost": similarity_boost,
        "speed": speed,
        "response_format": response_format,
        "lang": lang,
        "instructions": instructions,
    }
    provider_kwargs = type(tts_provider).PROVIDER_KWARGS
    if provider_kwargs:
        config.update({k: v for k, v in all_options.items() if k in provider_kwargs})

    console.print("[bold cyan]Configuration:[/bold cyan]")
    console.print(Pretty(config))

    # Show config file info
    if config_file:
        console.print(f"\n[dim]Config file loaded from: {config_manager.config_file}[/dim]")
    else:
        console.print(f"\n[dim]No config file found at: {config_manager.config_file}[/dim]")
        console.print("[dim]Use --create-config to create a sample configuration file[/dim]")


def handle_speech_generation(
    text: str,
    tts_provider: TTSProvider,
    provider: str,
    voice: str,
    model: str | None,
    output: Path | None,
    play_audio: bool,
    keep_temp: bool,
    temp_dir: Path | None,
    volume: float,
    debug: bool,
    stability: float,
    similarity_boost: float,
    speed: float,
    response_format: str,
    lang: str,
    instructions: str | None,
    audio_processing: AudioProcessingOptions | None = None,
) -> SpeechGenerationResult:
    """Generate and output speech.

    Args:
        text: Text to convert to speech.
        tts_provider: TTS provider instance.
        provider: Provider name.
        voice: Voice ID.
        model: Model name.
        output: Output file path.
        play_audio: Whether to play audio.
        keep_temp: Whether to keep temp files.
        temp_dir: Temp directory path.
        volume: Playback volume.
        debug: Debug mode.
        stability: ElevenLabs stability.
        similarity_boost: ElevenLabs similarity boost.
        speed: Speech speed.
        response_format: Audio format.
        lang: Language code.
        instructions: Voice instructions for OpenAI.
    """
    start_time = time.perf_counter()
    saved_path: Path | None = None
    output_bytes: int | None = None

    try:
        console.print("[cyan]Generating speech...[/cyan]")

        # Prepare provider-specific parameters
        kwargs = get_provider_kwargs(
            provider=provider,
            stability=stability,
            similarity_boost=similarity_boost,
            speed=speed,
            response_format=response_format,
            lang=lang,
            instructions=instructions,
        )

        # Derive audio suffix from the provider's default format
        audio_suffix = f".{tts_provider.supported_formats[0]}" if tts_provider.supported_formats else ".mp3"

        audio_data = tts_provider.generate_speech(
            text=text,
            voice=voice,
            model=model,
            **kwargs,
        )

        # Determine output file path
        if output:
            # User specified an output file
            output_path = Path(output)

            # If it's just a filename without directory, use temp_dir if specified
            if not output_path.is_absolute() and output_path.parent == Path("."):
                if temp_dir:
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    output_path = temp_dir / output_path
                    if debug:
                        console.print(f"[dim]Using temp directory for output: {temp_dir}[/dim]")

            # Ensure parent directory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            tts_provider.save_audio(audio_data, output_path)
            if audio_processing:
                postprocess_audio_file(output_path, audio_processing)
            saved_path = output_path
            output_bytes = output_path.stat().st_size if output_path.exists() else None
            console.print(f"[green]Audio saved to: {output_path}[/green]")

            if play_audio:
                console.print("[cyan]Playing audio...[/cyan]")
                # Read from saved file since iterator was consumed
                with open(output_path, "rb") as f:
                    audio_bytes = f.read()
                tts_provider.play_audio(audio_bytes, volume=volume)
        else:
            if play_audio:
                console.print("[cyan]Playing audio...[/cyan]")

                # Create temp file in specified directory or system temp
                if temp_dir:
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    with tempfile.NamedTemporaryFile(
                        suffix=audio_suffix, prefix="tts_", dir=str(temp_dir), delete=False
                    ) as tmp:
                        tmp_path = Path(tmp.name)
                else:
                    with tempfile.NamedTemporaryFile(suffix=audio_suffix, prefix="tts_", delete=False) as tmp:
                        tmp_path = Path(tmp.name)

                tts_provider.save_audio(audio_data, tmp_path)
                if audio_processing:
                    postprocess_audio_file(tmp_path, audio_processing)
                saved_path = tmp_path
                output_bytes = tmp_path.stat().st_size if tmp_path.exists() else None

                try:
                    # Read from saved file since iterator was consumed
                    with open(tmp_path, "rb") as f:
                        audio_bytes = f.read()
                    tts_provider.play_audio(audio_bytes, volume=volume)

                    if keep_temp or temp_dir:
                        console.print(f"[green]Audio saved to: {tmp_path}[/green]")
                        if keep_temp:
                            console.print("[dim]File kept as requested with --keep-temp[/dim]")
                        elif temp_dir:
                            console.print(f"[dim]File saved in specified directory: {temp_dir}[/dim]")
                finally:
                    # Clean up temp file after playback unless keep_temp is True or temp_dir is specified
                    if not keep_temp and not temp_dir and tmp_path.exists():
                        tmp_path.unlink()
                        saved_path = None
                        if debug:
                            console.print(f"[dim]Cleaned up temporary file: {tmp_path}[/dim]")
            else:
                # Save without playing - always keep the file
                if temp_dir:
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    with tempfile.NamedTemporaryFile(
                        suffix=audio_suffix, prefix="tts_", dir=str(temp_dir), delete=False
                    ) as tmp:
                        tmp_path = Path(tmp.name)
                else:
                    with tempfile.NamedTemporaryFile(suffix=audio_suffix, prefix="tts_", delete=False) as tmp:
                        tmp_path = Path(tmp.name)

                tts_provider.save_audio(audio_data, tmp_path)
                if audio_processing:
                    postprocess_audio_file(tmp_path, audio_processing)
                saved_path = tmp_path
                output_bytes = tmp_path.stat().st_size if tmp_path.exists() else None
                console.print(f"[green]Audio saved to: {tmp_path}[/green]")
                if temp_dir:
                    console.print(f"[dim]Saved in specified directory: {temp_dir}[/dim]")
                else:
                    console.print("[dim]File saved in system temp directory[/dim]")

        result = SpeechGenerationResult(
            provider=provider,
            model=model or tts_provider.default_model,
            voice=voice,
            text_length=len(text),
            output_path=saved_path,
            output_bytes=output_bytes,
            played=play_audio,
            elapsed_seconds=time.perf_counter() - start_time,
        )
        print_generation_summary(result)
        console.print("[green]Speech generation complete![/green]")
        return result

    except TTSError:
        raise
    except Exception as e:
        # Store debug mode for error handler
        set_debug_mode(debug)
        handle_error("Failed to generate speech", ErrorType.PROVIDER_ERROR, exception=e)


def handle_segmented_speech_generation(
    *,
    segments: list[TextSegment],
    tts_provider: TTSProvider,
    provider: str,
    default_voice: str,
    model: str | None,
    output: Path | None,
    play_audio: bool,
    keep_temp: bool,
    temp_dir: Path | None,
    volume: float,
    debug: bool,
    stability: float,
    similarity_boost: float,
    speed: float,
    response_format: str,
    lang: str,
    instructions: str | None,
    audio_processing: AudioProcessingOptions | None = None,
) -> None:
    """Generate speech for preprocessed text segments."""
    if output and len(segments) > 1:
        _handle_joined_segmented_output(
            segments=segments,
            tts_provider=tts_provider,
            provider=provider,
            default_voice=default_voice,
            model=model,
            output=output,
            play_audio=play_audio,
            volume=volume,
            stability=stability,
            similarity_boost=similarity_boost,
            speed=speed,
            response_format=response_format,
            lang=lang,
            instructions=instructions,
            audio_processing=audio_processing,
        )
        return

    for index, segment in enumerate(segments, start=1):
        segment_voice = segment.voice or default_voice
        try:
            resolved_voice = tts_provider.resolve_voice(segment_voice)
        except ValueError as e:
            handle_error(str(e), ErrorType.INVALID_VOICE, exception=e)

        console.print(f"[cyan]Generating segment {index}/{len(segments)}...[/cyan]")
        handle_speech_generation(
            text=segment.text,
            tts_provider=tts_provider,
            provider=provider,
            voice=resolved_voice,
            model=model,
            output=output if len(segments) == 1 else None,
            play_audio=play_audio,
            keep_temp=keep_temp,
            temp_dir=temp_dir,
            volume=volume,
            debug=debug,
            stability=stability,
            similarity_boost=similarity_boost,
            speed=segment.speed if segment.speed is not None else speed,
            response_format=response_format,
            lang=segment.lang or lang,
            instructions=instructions,
            audio_processing=audio_processing,
        )
        if segment.pause_after_ms > 0:
            time.sleep(segment.pause_after_ms / 1000)


def _handle_joined_segmented_output(
    *,
    segments: list[TextSegment],
    tts_provider: TTSProvider,
    provider: str,
    default_voice: str,
    model: str | None,
    output: Path,
    play_audio: bool,
    volume: float,
    stability: float,
    similarity_boost: float,
    speed: float,
    response_format: str,
    lang: str,
    instructions: str | None,
    audio_processing: AudioProcessingOptions | None = None,
) -> None:
    """Generate segment files and join them into the requested output path."""
    suffix = f".{tts_provider.supported_formats[0]}" if tts_provider.supported_formats else ".mp3"
    with tempfile.TemporaryDirectory(prefix="par_tts_segments_") as temp_dir_name:
        chunk_paths: list[Path] = []
        temp_dir = Path(temp_dir_name)
        for index, segment in enumerate(segments, start=1):
            segment_voice = segment.voice or default_voice
            try:
                resolved_voice = tts_provider.resolve_voice(segment_voice)
            except ValueError as e:
                handle_error(str(e), ErrorType.INVALID_VOICE, exception=e)

            kwargs = get_provider_kwargs(
                provider=provider,
                stability=stability,
                similarity_boost=similarity_boost,
                speed=segment.speed if segment.speed is not None else speed,
                response_format=response_format,
                lang=segment.lang or lang,
                instructions=instructions,
            )
            chunk_path = temp_dir / f"segment_{index:04d}{suffix}"
            console.print(f"[cyan]Generating segment {index}/{len(segments)}...[/cyan]")
            audio_data = tts_provider.generate_speech(segment.text, resolved_voice, model=model, **kwargs)
            tts_provider.save_audio(audio_data, chunk_path)
            chunk_paths.append(chunk_path)
            if segment.pause_after_ms > 0:
                time.sleep(segment.pause_after_ms / 1000)

        concat_audio_files(chunk_paths, output)
        if audio_processing:
            postprocess_audio_file(output, audio_processing)
        console.print(f"[green]Audio saved to: {output}[/green]")
        if play_audio:
            console.print("[cyan]Playing audio...[/cyan]")
            tts_provider.play_audio(output.read_bytes(), volume=volume)
        print_generation_summary(
            SpeechGenerationResult(
                provider=provider,
                model=model or tts_provider.default_model,
                voice=default_voice,
                text_length=sum(len(segment.text) for segment in segments),
                output_path=output,
                output_bytes=output.stat().st_size if output.exists() else None,
                played=play_audio,
                elapsed_seconds=0.0,
            )
        )


def _metadata_float(record: BatchRecord, key: str, default: float) -> float:
    metadata = record.metadata or {}
    value = metadata.get(key, default)
    try:
        return float(value)
    except (TypeError, ValueError):
        handle_error(f"Invalid batch {key!r} value: {value}", ErrorType.INVALID_INPUT)


def _metadata_str(record: BatchRecord, key: str, default: str | None) -> str | None:
    metadata = record.metadata or {}
    value = metadata.get(key, default)
    return str(value) if value is not None else None


def _write_timestamps_for_text(path: Path, text: str, timestamp_format: str) -> None:
    segments = split_caption_segments(text) or [text.strip()]
    entries = build_timestamp_entries(segments)
    try:
        write_timestamp_export(path, entries, output_format=timestamp_format)
    except ValueError as e:
        handle_error(str(e), ErrorType.INVALID_INPUT, exception=e)
    console.print(f"[green]Timestamps saved to: {path}[/green]")


def _resolve_batch_output_dir(batch_output_dir: Path | None) -> Path:
    output_dir = batch_output_dir or Path.cwd()
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir


def handle_batch_synthesis(
    *,
    batch_file: Path,
    batch_output_dir: Path | None,
    template_variables: dict[str, str],
    tts_provider: TTSProvider,
    provider: str,
    default_voice: str,
    model: str | None,
    play_audio: bool,
    keep_temp: bool,
    temp_dir: Path | None,
    volume: float,
    debug: bool,
    stability: float,
    similarity_boost: float,
    speed: float,
    response_format: str,
    lang: str,
    instructions: str | None,
    audio_processing: AudioProcessingOptions | None,
    timestamp_format: str,
) -> None:
    """Generate one audio file for each row in a CSV/JSONL batch."""
    try:
        records = parse_batch_records(batch_file)
    except (OSError, ValueError) as e:
        handle_error(f"Failed to read batch file '{batch_file}'", ErrorType.INVALID_INPUT, exception=e)
    if not records:
        handle_error("Batch file contains no records", ErrorType.INVALID_INPUT)

    output_dir = _resolve_batch_output_dir(batch_output_dir)
    suffix = f".{tts_provider.supported_formats[0]}" if tts_provider.supported_formats else ".mp3"
    for index, record in enumerate(records, start=1):
        text = render_template(record.text, template_variables) if template_variables else record.text
        row_voice = _metadata_str(record, "voice", default_voice) or default_voice
        try:
            resolved_voice = tts_provider.resolve_voice(row_voice)
        except ValueError as e:
            handle_error(str(e), ErrorType.INVALID_VOICE, exception=e)
        output_path = output_path_for_record(record, output_dir=output_dir, index=index, suffix=suffix)
        console.print(f"[cyan]Processing batch item {index}/{len(records)}...[/cyan]")
        handle_speech_generation(
            text=text,
            tts_provider=tts_provider,
            provider=provider,
            voice=resolved_voice,
            model=_metadata_str(record, "model", model),
            output=output_path,
            play_audio=play_audio,
            keep_temp=keep_temp,
            temp_dir=temp_dir,
            volume=volume,
            debug=debug,
            stability=_metadata_float(record, "stability", stability),
            similarity_boost=_metadata_float(record, "similarity_boost", similarity_boost),
            speed=_metadata_float(record, "speed", speed),
            response_format=_metadata_str(record, "response_format", response_format) or response_format,
            lang=_metadata_str(record, "lang", lang) or lang,
            instructions=_metadata_str(record, "instructions", instructions),
            audio_processing=audio_processing,
        )
        timestamp_output = record.metadata.get("timestamps") if record.metadata else None
        if timestamp_output:
            _write_timestamps_for_text(Path(str(timestamp_output)), text, timestamp_format)
    console.print(f"[green]Batch synthesis complete: {len(records)} item(s)[/green]")


def _read_watch_file(path: Path) -> str:
    validate_file_path(str(path), must_exist=True)
    _validate_file_read_safety(path.resolve())
    try:
        return path.read_text(encoding="utf-8")
    except OSError as e:
        handle_error(f"Failed to read watched file '{path}'", ErrorType.FILE_NOT_FOUND, exception=e)


def handle_watch_synthesis(
    *,
    watch_path: Path,
    watch_once: bool,
    watch_interval: float,
    batch_output_dir: Path | None,
    template_variables: dict[str, str],
    tts_provider: TTSProvider,
    provider: str,
    voice: str,
    model: str | None,
    play_audio: bool,
    keep_temp: bool,
    temp_dir: Path | None,
    volume: float,
    debug: bool,
    stability: float,
    similarity_boost: float,
    speed: float,
    response_format: str,
    lang: str,
    instructions: str | None,
    audio_processing: AudioProcessingOptions | None,
) -> None:
    """Regenerate audio for watched document files."""
    try:
        files = discover_watch_inputs(watch_path)
    except ValueError as e:
        handle_error(str(e), ErrorType.INVALID_INPUT, exception=e)
    if not files:
        handle_error("Watch path contains no supported text files", ErrorType.INVALID_INPUT)

    output_dir = _resolve_batch_output_dir(batch_output_dir)
    suffix = f".{tts_provider.supported_formats[0]}" if tts_provider.supported_formats else ".mp3"

    def synthesize_files(paths: list[Path]) -> None:
        for path in paths:
            text = _read_watch_file(path).strip()
            if not text:
                console.print(f"[yellow]Skipping empty watched file: {path}[/yellow]")
                continue
            if template_variables:
                text = render_template(text, template_variables)
            output_path = output_dir / f"{path.stem}{suffix}"
            console.print(f"[cyan]Regenerating audio for {path}...[/cyan]")
            handle_speech_generation(
                text=text,
                tts_provider=tts_provider,
                provider=provider,
                voice=voice,
                model=model,
                output=output_path,
                play_audio=play_audio,
                keep_temp=keep_temp,
                temp_dir=temp_dir,
                volume=volume,
                debug=debug,
                stability=stability,
                similarity_boost=similarity_boost,
                speed=speed,
                response_format=response_format,
                lang=lang,
                instructions=instructions,
                audio_processing=audio_processing,
            )

    synthesize_files(files)
    if watch_once:
        return

    console.print(f"[cyan]Watching {watch_path} every {watch_interval:.1f}s. Press Ctrl+C to stop.[/cyan]")
    previous = watch_snapshot(watch_path)
    try:
        while True:
            time.sleep(watch_interval)
            current = watch_snapshot(watch_path)
            changed = changed_watch_inputs(previous, current)
            if changed:
                synthesize_files(changed)
            previous = current
    except KeyboardInterrupt:
        console.print("[yellow]Watch mode stopped.[/yellow]")


@app.command()
def main(
    text: Annotated[
        str | None, typer.Argument(help="Text to convert to speech. Use '-' for stdin, '@filename' to read from file")
    ] = None,
    provider: Annotated[
        str | None,
        typer.Option(
            "-P",
            "--provider",
            help="TTS provider to use (elevenlabs, openai, kokoro-onnx, deepgram, gemini)",
            envvar="TTS_PROVIDER",
        ),
    ] = None,
    voice: Annotated[
        str | None,
        typer.Option(
            "-v",
            "--voice",
            help="Voice name or ID to use for TTS",
            envvar="TTS_VOICE_ID",
        ),
    ] = None,
    output: Annotated[
        Path | None,
        typer.Option(
            "-o",
            "--output",
            help="Output file path for audio",
        ),
    ] = None,
    model: Annotated[
        str | None,
        typer.Option(
            "-m",
            "--model",
            help="Model to use (provider-specific)",
        ),
    ] = None,
    profile: Annotated[
        str | None,
        typer.Option(
            "--profile",
            help="Named config profile to apply",
        ),
    ] = None,
    play_audio: Annotated[
        bool,
        typer.Option(
            "-p",
            "--play/--no-play",
            help="Play audio after generation",
        ),
    ] = True,
    keep_temp: Annotated[
        bool,
        typer.Option(
            "-k",
            "--keep-temp",
            help="Keep temporary audio files after playback",
        ),
    ] = False,
    temp_dir: Annotated[
        Path | None,
        typer.Option(
            "-t",
            "--temp-dir",
            help="Directory for temporary audio files (default: system temp)",
        ),
    ] = None,
    # Provider-specific options
    stability: Annotated[
        float | None,
        typer.Option(
            "-s",
            "--stability",
            help="Voice stability for ElevenLabs (0.0 to 1.0)",
            min=0.0,
            max=1.0,
        ),
    ] = None,
    similarity_boost: Annotated[
        float | None,
        typer.Option(
            "-S",
            "--similarity",
            help="Voice similarity boost for ElevenLabs (0.0 to 1.0)",
            min=0.0,
            max=1.0,
        ),
    ] = None,
    speed: Annotated[
        float | None,
        typer.Option(
            "-r",
            "--speed",
            help="Speech speed for OpenAI/Kokoro (0.25 to 4.0)",
            min=0.25,
            max=4.0,
        ),
    ] = None,
    response_format: Annotated[
        str | None,
        typer.Option(
            "-f",
            "--format",
            help="Audio format for OpenAI (mp3, opus, aac, flac, wav)",
        ),
    ] = None,
    lang: Annotated[
        str | None,
        typer.Option(
            "-g",
            "--lang",
            help="Language code for Kokoro ONNX (e.g., en-us)",
        ),
    ] = None,
    instructions: Annotated[
        str | None,
        typer.Option(
            "-i",
            "--instructions",
            help="Voice instructions for OpenAI gpt-4o-mini-tts (e.g., 'Speak in a cheerful tone')",
        ),
    ] = None,
    volume: Annotated[
        float | None,
        typer.Option(
            "-w",
            "--volume",
            help="Playback volume (0.0 = silent, 1.0 = normal, 2.0 = double)",
            min=0.0,
            max=5.0,
        ),
    ] = None,
    # Text and audio processing options
    chunk: Annotated[
        bool,
        typer.Option(
            "--chunk",
            help="Split long input into sentence-aware chunks before synthesis",
        ),
    ] = False,
    max_chars: Annotated[
        int | None,
        typer.Option(
            "--max-chars",
            help="Maximum characters per chunk when --chunk is enabled",
            min=1,
        ),
    ] = None,
    markup: Annotated[
        bool,
        typer.Option(
            "--markup",
            help="Parse lightweight SSML-like markup before synthesis",
        ),
    ] = False,
    voice_sections: Annotated[
        bool,
        typer.Option(
            "--voice-sections",
            help="Parse per-paragraph 'voice=nova; speed=1.1 | text' sections",
        ),
    ] = False,
    pronunciation: Annotated[
        list[str] | None,
        typer.Option(
            "--pronunciation",
            help="Pronunciation replacement as WORD=spoken form; may be repeated",
        ),
    ] = None,
    pronunciation_file: Annotated[
        Path | None,
        typer.Option(
            "--pronunciation-file",
            help="YAML mapping file of pronunciation replacements",
        ),
    ] = None,
    auto_lang: Annotated[
        bool,
        typer.Option(
            "--auto-lang",
            help="Detect language from input text and pass language hints where supported",
        ),
    ] = False,
    normalize: Annotated[
        bool,
        typer.Option(
            "--normalize",
            help="Normalize generated audio with ffmpeg",
        ),
    ] = False,
    trim_silence: Annotated[
        bool,
        typer.Option(
            "--trim-silence",
            help="Trim leading silence from generated audio with ffmpeg",
        ),
    ] = False,
    post_process_preset: Annotated[
        str | None,
        typer.Option(
            "--post-process-preset",
            help="Audio post-processing preset: podcast or notification",
        ),
    ] = None,
    fade_in_ms: Annotated[
        int | None,
        typer.Option(
            "--fade-in-ms",
            help="Fade-in duration in milliseconds",
            min=0,
        ),
    ] = None,
    fade_out_ms: Annotated[
        int | None,
        typer.Option(
            "--fade-out-ms",
            help="Fade-out duration in milliseconds",
            min=0,
        ),
    ] = None,
    # Utility options
    debug: Annotated[
        bool,
        typer.Option(
            "-d",
            "--debug",
            help="Show debug information",
        ),
    ] = False,
    structured_logs: Annotated[
        bool,
        typer.Option(
            "--structured-logs",
            help="Emit JSON logs for automation and telemetry ingestion",
        ),
    ] = False,
    log_level: Annotated[
        str | None,
        typer.Option(
            "--log-level",
            help="Logging level for CLI/provider diagnostics (DEBUG, INFO, WARNING, ERROR, CRITICAL)",
        ),
    ] = None,
    retry_attempts: Annotated[
        int | None,
        typer.Option(
            "--retry-attempts",
            help="Retries after the initial provider attempt",
            min=0,
            max=10,
        ),
    ] = None,
    retry_backoff: Annotated[
        float | None,
        typer.Option(
            "--retry-backoff",
            help="Initial exponential retry backoff in seconds",
            min=0.0,
            max=60.0,
        ),
    ] = None,
    list_voices: Annotated[
        bool,
        typer.Option(
            "-l",
            "--list",
            help="List available voices and exit",
        ),
    ] = False,
    preview_voice: Annotated[
        str | None,
        typer.Option(
            "-V",
            "--preview-voice",
            help="Preview a voice with sample text and exit",
        ),
    ] = None,
    list_providers: Annotated[
        bool,
        typer.Option(
            "-L",
            "--list-providers",
            help="List available providers and exit",
        ),
    ] = False,
    capabilities: Annotated[
        bool,
        typer.Option(
            "--capabilities",
            help="Show provider capability matrix and exit",
        ),
    ] = False,
    list_voice_packs: Annotated[
        bool,
        typer.Option(
            "--list-voice-packs",
            help="List bundled voice packs and exit",
        ),
    ] = False,
    show_voice_pack: Annotated[
        str | None,
        typer.Option(
            "--show-voice-pack",
            metavar="PACK",
            help="Show bundled voice-pack recommendations and exit",
        ),
    ] = None,
    completion: Annotated[
        str | None,
        typer.Option(
            "--completion",
            metavar="SHELL",
            help="Print shell completion script for bash, zsh, or fish and exit",
        ),
    ] = None,
    completion_install: Annotated[
        str | None,
        typer.Option(
            "--completion-install",
            metavar="SHELL",
            help="Print shell completion installation instructions and exit",
        ),
    ] = None,
    dump_config: Annotated[
        bool,
        typer.Option(
            "-D",
            "--dump",
            help="Dump configuration and exit",
        ),
    ] = False,
    dry_run: Annotated[
        bool,
        typer.Option(
            "--dry-run",
            help="Show the resolved operation plan without generating speech",
        ),
    ] = False,
    estimate_cost: Annotated[
        bool,
        typer.Option(
            "--estimate-cost",
            help="Estimate synthesis cost without generating speech",
        ),
    ] = False,
    benchmark: Annotated[
        bool,
        typer.Option(
            "--benchmark",
            help="Run objective provider benchmark for the input text",
        ),
    ] = False,
    benchmark_providers: Annotated[
        list[str] | None,
        typer.Option(
            "--benchmark-provider",
            help="Provider to include in --benchmark; may be repeated (defaults to --provider)",
        ),
    ] = None,
    benchmark_repeat: Annotated[
        int,
        typer.Option(
            "--benchmark-repeat",
            help="Number of synthesis runs per benchmark provider",
            min=1,
        ),
    ] = 1,
    search_voices: Annotated[
        str | None,
        typer.Option(
            "--search-voices",
            help="Search voices by name, ID, labels, or category and exit",
        ),
    ] = None,
    from_clipboard: Annotated[
        bool,
        typer.Option(
            "--from-clipboard",
            help="Read input text from the system clipboard",
        ),
    ] = False,
    watch_stdin: Annotated[
        bool,
        typer.Option(
            "--watch-stdin",
            help="Read stdin line-by-line and synthesize each non-empty line until EOF",
        ),
    ] = False,
    batch: Annotated[
        Path | None,
        typer.Option(
            "--batch",
            help="CSV/JSONL batch input with text plus optional metadata columns",
        ),
    ] = None,
    batch_output_dir: Annotated[
        Path | None,
        typer.Option(
            "--batch-output-dir",
            help="Directory for batch/watch generated audio files",
        ),
    ] = None,
    template_vars: Annotated[
        list[str] | None,
        typer.Option(
            "--var",
            help="Template variable as KEY=VALUE; may be repeated for @templates, batch rows, and watch files",
        ),
    ] = None,
    watch_path: Annotated[
        Path | None,
        typer.Option(
            "--watch",
            help="Watch a text file or folder and regenerate audio when documents change",
        ),
    ] = None,
    watch_once: Annotated[
        bool,
        typer.Option(
            "--watch-once",
            help="Process current --watch inputs once, then exit",
        ),
    ] = False,
    watch_interval: Annotated[
        float,
        typer.Option(
            "--watch-interval",
            help="Polling interval in seconds for --watch",
            min=0.1,
        ),
    ] = 1.0,
    timestamp_output: Annotated[
        Path | None,
        typer.Option(
            "--timestamp-output",
            help="Write rough sentence/chunk timing metadata to .json or .srt",
        ),
    ] = None,
    timestamp_format: Annotated[
        str,
        typer.Option(
            "--timestamp-format",
            help="Timestamp export format: json or srt",
        ),
    ] = "json",
    notification: Annotated[
        bool,
        typer.Option(
            "--notification",
            help="Use low-latency defaults for short notification messages",
        ),
    ] = False,
    refresh_cache: Annotated[
        bool,
        typer.Option(
            "--refresh-cache",
            help="Force refresh voice cache (ElevenLabs only)",
        ),
    ] = False,
    clear_cache_samples: Annotated[
        bool,
        typer.Option(
            "--clear-cache-samples",
            help="Clear cached voice samples",
        ),
    ] = False,
    create_config: Annotated[
        bool,
        typer.Option(
            "--create-config",
            help="Create a sample configuration file",
        ),
    ] = False,
    yes: Annotated[
        bool,
        typer.Option(
            "-y",
            "--yes",
            help="Answer yes to confirmations (e.g. overwriting an existing config)",
        ),
    ] = False,
    clear_kokoro_models: Annotated[
        bool,
        typer.Option(
            "--clear-kokoro-models",
            help="Clear downloaded Kokoro ONNX models",
        ),
    ] = False,
) -> None:
    """
    Convert text to speech using various TTS providers.

    This tool accepts text as input and converts it to speech using the
    specified TTS provider. Voices can be configured via command line options
    or environment variables.
    """
    if completion:
        try:
            handle_completion(completion)
        except TTSError as exc:
            console.print(f"[red]{exc.error_type.display_name}:[/red] {exc.message}")
            raise typer.Exit(exc.error_type.exit_code) from exc
        return

    if completion_install:
        try:
            handle_completion_install(completion_install)
        except TTSError as exc:
            console.print(f"[red]{exc.error_type.display_name}:[/red] {exc.message}")
            raise typer.Exit(exc.error_type.exit_code) from exc
        return

    if list_voice_packs:
        try:
            handle_list_voice_packs()
        except TTSError as exc:
            console.print(f"[red]{exc.error_type.display_name}:[/red] {exc.message}")
            raise typer.Exit(exc.error_type.exit_code) from exc
        return

    if show_voice_pack:
        try:
            handle_show_voice_pack(show_voice_pack)
        except TTSError as exc:
            console.print(f"[red]{exc.error_type.display_name}:[/red] {exc.message}")
            raise typer.Exit(exc.error_type.exit_code) from exc
        return

    load_dotenv()

    # Handle config operations
    config_manager = ConfigManager()
    if handle_config_operations(create_config, config_manager, force=yes):
        return

    # Load configuration file
    config_file = config_manager.load_config()
    if config_file and profile:
        try:
            config_file = config_manager.apply_profile(config_file, profile)
            console.print(f"[dim]Applied profile: {profile}[/dim]")
        except ValueError as e:
            handle_error(str(e), ErrorType.CONFIG_ERROR, exception=e)

    # Apply config file defaults (CLI args override these)
    if config_file:
        provider = provider or config_file.provider
        # Voice resolution: per-provider `voices` mapping takes precedence; the legacy
        # global `voice` field is only applied when the active provider matches the one
        # the config was written for. Same provider-match rule for `model`.
        if not voice:
            if config_file.voices and provider and provider in config_file.voices:
                voice = config_file.voices[provider]
            elif provider == config_file.provider:
                voice = config_file.voice
        if not model and provider == config_file.provider:
            model = config_file.model
        output = output or (Path(config_file.output_dir) / "output.mp3" if config_file.output_dir else None)
        # Use is-None checks so explicitly-passed CLI values (including defaults
        # like --speed 1.0) are never overridden by the config file.
        response_format = response_format if response_format is not None else (config_file.output_format or "mp3")
        keep_temp = keep_temp if keep_temp else config_file.keep_temp or False
        temp_dir = temp_dir or (Path(config_file.temp_dir) if config_file.temp_dir else None)
        volume = volume if volume is not None else (config_file.volume or 1.0)
        speed = speed if speed is not None else (config_file.speed or 1.0)
        stability = stability if stability is not None else (config_file.stability or 0.5)
        similarity_boost = similarity_boost if similarity_boost is not None else (config_file.similarity_boost or 0.5)
        lang = lang if lang is not None else (config_file.lang or "en-us")
        # CLI default is True. `--no-play` flips it to False — respect that explicit
        # override. Only fall through to the config value when the CLI value is still
        # the default (True); we cannot distinguish "user typed --play" from "user
        # passed nothing", so the config can override the True default but not False.
        if play_audio and config_file.play_audio is not None:
            play_audio = config_file.play_audio
        chunk = chunk or config_file.chunk or False
        max_chars = max_chars if max_chars is not None else (config_file.max_chars or 1200)
        markup = markup or config_file.markup or False
        voice_sections = voice_sections or config_file.voice_sections or False
        pronunciation_file = pronunciation_file or (
            Path(config_file.pronunciation_file) if config_file.pronunciation_file else None
        )
        auto_lang = auto_lang or config_file.auto_lang or False
        normalize = normalize or config_file.normalize or False
        trim_silence = trim_silence or config_file.trim_silence or False
        post_process_preset = post_process_preset or config_file.post_process_preset
        fade_in_ms = fade_in_ms if fade_in_ms is not None else (config_file.fade_in_ms or 0)
        fade_out_ms = fade_out_ms if fade_out_ms is not None else (config_file.fade_out_ms or 0)
        debug = debug or config_file.debug or False
        structured_logs = structured_logs or config_file.structured_logs or False
        log_level = log_level or config_file.log_level
        retry_attempts = retry_attempts if retry_attempts is not None else (config_file.retry_attempts or 0)
        retry_backoff = retry_backoff if retry_backoff is not None else (config_file.retry_backoff or 0.0)

    # Apply hardcoded defaults for any values still unset (no CLI arg, no config).
    if response_format is None:
        response_format = "mp3"
    if volume is None:
        volume = 1.0
    if speed is None:
        speed = 1.0
    if stability is None:
        stability = 0.5
    if similarity_boost is None:
        similarity_boost = 0.5
    if lang is None:
        lang = "en-us"
    if max_chars is None:
        max_chars = 1200
    if fade_in_ms is None:
        fade_in_ms = 0
    if fade_out_ms is None:
        fade_out_ms = 0
    if log_level is None:
        log_level = "DEBUG" if debug else "WARNING"
    if retry_attempts is None:
        retry_attempts = 0
    if retry_backoff is None:
        retry_backoff = 0.0

    # Apply default provider if still not set
    if not provider:
        provider = DEFAULT_PROVIDER

    requested_voice = voice

    # Store debug mode globally for error handler and configure process logging.
    set_debug_mode(debug)
    try:
        configure_logging(structured=structured_logs, level=log_level)
    except ValueError as e:
        handle_error(str(e), ErrorType.CONFIG_ERROR, exception=e)

    if watch_stdin and text is not None:
        handle_error("Use either TEXT or --watch-stdin, not both", ErrorType.INVALID_INPUT)
    if watch_stdin and output is not None:
        handle_error(
            "--watch-stdin cannot be combined with --output because it would overwrite files", ErrorType.INVALID_INPUT
        )
    if batch and text is not None:
        handle_error("Use either TEXT or --batch, not both", ErrorType.INVALID_INPUT)
    if batch and output is not None:
        handle_error(
            "--batch cannot be combined with --output because each row writes its own file", ErrorType.INVALID_INPUT
        )
    if watch_path and text is not None:
        handle_error("Use either TEXT or --watch, not both", ErrorType.INVALID_INPUT)
    if watch_path and output is not None:
        handle_error("--watch cannot be combined with --output; use --batch-output-dir", ErrorType.INVALID_INPUT)
    if watch_once and watch_path is None:
        handle_error("--watch-once requires --watch", ErrorType.INVALID_INPUT)
    if timestamp_format not in {"json", "srt"}:
        handle_error("--timestamp-format must be 'json' or 'srt'", ErrorType.INVALID_INPUT)

    # Check if text is required (not needed for certain operations)
    text_required = not (
        list_providers
        or capabilities
        or list_voice_packs
        or show_voice_pack
        or completion
        or completion_install
        or list_voices
        or preview_voice
        or dump_config
        or refresh_cache
        or clear_cache_samples
        or clear_kokoro_models
        or search_voices
        or from_clipboard
        or watch_stdin
        or batch
        or watch_path
    )

    # Handle input operations
    text = handle_input_operations(text, text_required, from_clipboard=from_clipboard)

    if text == "doctor":
        handle_doctor()
        return

    try:
        template_variables = parse_template_vars(template_vars)
    except ValueError as e:
        handle_error(str(e), ErrorType.INVALID_INPUT, exception=e)
    if template_variables and text:
        text = render_template(text, template_variables)

    if notification:
        notification_defaults = NotificationDefaults.from_options(provider=provider, model=model, play_audio=play_audio)
        model = notification_defaults.model
        speed = notification_defaults.speed
        post_process_preset = post_process_preset or notification_defaults.post_process_preset
        trim_silence = True if notification_defaults.trim_silence else trim_silence
        play_audio = notification_defaults.play_audio

    # Handle list providers
    if list_providers:
        handle_list_providers()
        return

    if capabilities:
        handle_capabilities()
        return

    if not voice:
        voice = get_default_voice(provider)

    if dry_run:
        if not text:
            handle_error("No text provided for dry run", ErrorType.INVALID_INPUT)
        print_dry_run_plan(
            build_operation_plan(
                provider=provider,
                voice=voice,
                model=model,
                text=text,
                output=output,
                play_audio=play_audio,
                keep_temp=keep_temp,
                temp_dir=temp_dir,
                volume=volume,
                stability=stability,
                similarity_boost=similarity_boost,
                speed=speed,
                response_format=response_format,
                lang=lang,
                instructions=instructions,
                retry_attempts=retry_attempts,
                retry_backoff=retry_backoff,
            )
        )
        return

    if estimate_cost:
        if not text:
            handle_error("No text provided for cost estimate", ErrorType.INVALID_INPUT)
        print_cost_estimate(estimate_synthesis_cost(provider, model, text))
        return

    if benchmark:
        if not text:
            handle_error("No text provided for benchmark", ErrorType.INVALID_INPUT)
        selected_providers = benchmark_providers or [provider]
        benchmark_results: list[VoiceBenchmarkResult] = []
        for benchmark_provider in selected_providers:
            provider_instance = create_provider(
                benchmark_provider,
                config_file,
                retry_attempts=retry_attempts,
                retry_backoff=retry_backoff,
            )
            benchmark_plugin = get_provider_plugin(benchmark_provider)
            benchmark_voice = requested_voice or benchmark_plugin.default_voice or get_default_voice(benchmark_provider)
            try:
                benchmark_voice = provider_instance.resolve_voice(benchmark_voice)
            except ValueError as e:
                handle_error(str(e), ErrorType.INVALID_VOICE, exception=e)
            benchmark_results.extend(
                run_provider_benchmark(
                    tts_provider=provider_instance,
                    provider=benchmark_provider,
                    text=text,
                    voice=benchmark_voice,
                    model=model,
                    repeat_count=benchmark_repeat,
                    stability=stability,
                    similarity_boost=similarity_boost,
                    speed=speed,
                    response_format=response_format,
                    lang=lang,
                    instructions=instructions,
                )
            )
        print_voice_benchmark(benchmark_results)
        return

    # Create provider
    tts_provider = create_provider(
        provider,
        config_file,
        retry_attempts=retry_attempts,
        retry_backoff=retry_backoff,
    )

    # Handle cache management operations (ElevenLabs only)
    if refresh_cache or clear_cache_samples:
        if provider == "elevenlabs":
            from par_tts.providers.elevenlabs import ElevenLabsProvider
            from par_tts.voice_cache import VoiceCache

            if isinstance(tts_provider, ElevenLabsProvider):
                cache = VoiceCache("par-tts-elevenlabs")

                if refresh_cache:
                    console.print("[cyan]Force refreshing voice cache...[/cyan]")
                    if cache.refresh_cache(tts_provider.client):
                        console.print("[green]Voice cache refreshed successfully[/green]")
                    else:
                        console.print("[yellow]Voice cache is already up to date[/yellow]")

                if clear_cache_samples:
                    console.print("[cyan]Clearing cached voice samples...[/cyan]")
                    cache.clear_cache(keep_samples=False)
                    console.print("[green]Voice samples cleared[/green]")

                return
        else:
            console.print("[yellow]Cache management is only available for ElevenLabs provider[/yellow]")
            return

    # Handle clear Kokoro models
    if clear_kokoro_models:
        from par_tts.model_downloader import ModelDownloader

        downloader = ModelDownloader()
        if downloader.models_exist():
            console.print("[cyan]Clearing Kokoro ONNX models...[/cyan]")
            downloader.clear_models()
            console.print("[green]Kokoro models cleared successfully[/green]")
        else:
            console.print("[yellow]No Kokoro models found to clear[/yellow]")
        return

    # Handle list voices
    if list_voices:
        handle_list_voices(tts_provider)
        return

    # Handle voice search
    if search_voices:
        handle_voice_search(tts_provider, search_voices)
        return

    # Handle voice preview
    if preview_voice:
        handle_voice_preview(preview_voice, tts_provider, provider, model, volume)
        return

    # Get default voice if not specified
    if not voice:
        voice = get_default_voice(provider)
        if not voice:
            voice = tts_provider.default_voice

    # Handle dump config
    if dump_config:
        handle_dump_config(
            provider,
            voice,
            model,
            output,
            play_audio,
            keep_temp,
            temp_dir,
            stability,
            similarity_boost,
            speed,
            response_format,
            lang,
            instructions,
            structured_logs,
            log_level,
            retry_attempts,
            retry_backoff,
            config_file,
            config_manager,
            tts_provider,
        )
        return

    audio_processing = AudioProcessingOptions(
        normalize=normalize,
        trim_silence=trim_silence,
        preset=post_process_preset,
        fade_in_ms=fade_in_ms,
        fade_out_ms=fade_out_ms,
    )
    if not audio_processing.enabled:
        audio_processing = None

    if batch:
        handle_batch_synthesis(
            batch_file=batch,
            batch_output_dir=batch_output_dir,
            template_variables=template_variables,
            tts_provider=tts_provider,
            provider=provider,
            default_voice=voice,
            model=model,
            play_audio=play_audio,
            keep_temp=keep_temp,
            temp_dir=temp_dir,
            volume=volume,
            debug=debug,
            stability=stability,
            similarity_boost=similarity_boost,
            speed=speed,
            response_format=response_format,
            lang=lang,
            instructions=instructions,
            audio_processing=audio_processing,
            timestamp_format=timestamp_format,
        )
        return

    if watch_path:
        try:
            voice = tts_provider.resolve_voice(voice)
        except ValueError as e:
            handle_error(str(e), ErrorType.INVALID_VOICE, exception=e)
        handle_watch_synthesis(
            watch_path=watch_path,
            watch_once=watch_once,
            watch_interval=watch_interval,
            batch_output_dir=batch_output_dir,
            template_variables=template_variables,
            tts_provider=tts_provider,
            provider=provider,
            voice=voice,
            model=model,
            play_audio=play_audio,
            keep_temp=keep_temp,
            temp_dir=temp_dir,
            volume=volume,
            debug=debug,
            stability=stability,
            similarity_boost=similarity_boost,
            speed=speed,
            response_format=response_format,
            lang=lang,
            instructions=instructions,
            audio_processing=audio_processing,
        )
        return

    config_pronunciations = config_file.pronunciations if config_file else None
    pronunciations = merge_pronunciations(
        config_pronunciations,
        load_pronunciation_file(pronunciation_file),
        parse_pronunciation_options(pronunciation),
    )
    pipeline_enabled = bool(chunk or markup or voice_sections or pronunciations or auto_lang)

    # Resolve voice
    original_voice = voice
    if not pipeline_enabled:
        try:
            voice = tts_provider.resolve_voice(voice)
            if debug and original_voice != voice:
                console.print(f"[dim]Resolved '{original_voice}' to voice ID: {voice}[/dim]")
        except ValueError as e:
            handle_error(str(e), ErrorType.INVALID_VOICE, exception=e)

    # Debug information
    if debug:
        from par_tts.utils import sanitize_debug_output

        debug_info = {
            "Provider": provider,
            "Text_length": f"{len(text)} characters" if text else "N/A",
            "Voice_input": original_voice,
            "Voice_ID": voice,
            "Model": model or "default",
        }

        # Only collect known TTS-related environment variables (not a broad scan)
        _known_env_vars = [
            "ELEVENLABS_API_KEY",
            "OPENAI_API_KEY",
            "DEEPGRAM_API_KEY",
            "DG_API_KEY",
            "GEMINI_API_KEY",
            "GOOGLE_API_KEY",
            "TTS_PROVIDER",
            "TTS_VOICE_ID",
            "ELEVENLABS_VOICE_ID",
            "OPENAI_VOICE_ID",
            "KOKORO_VOICE_ID",
            "DEEPGRAM_VOICE_ID",
            "GEMINI_VOICE_ID",
            "KOKORO_MODEL_PATH",
            "KOKORO_VOICE_PATH",
        ]
        env_vars = {k: os.environ[k] for k in _known_env_vars if k in os.environ}
        sanitized_env = sanitize_debug_output(env_vars)

        console.print("[bold cyan]Debug Information:[/bold cyan]")
        for key, value in debug_info.items():
            console.print(f"  {key}: {value}")

        if env_vars:
            console.print("\n[bold cyan]Environment Variables (sanitized):[/bold cyan]")
            for key, value in sanitized_env.items():
                console.print(f"  {key}: {value}")

        console.print(f"  Output_file: {output or 'None'}")
        console.print(f"  Play_audio: {play_audio}")
        if temp_dir:
            console.print(f"  Temp directory: {temp_dir}")
        console.print()

    # Handle preprocessed/segmented generation
    if pipeline_enabled and text:
        segments = build_text_segments(
            text,
            pronunciations=pronunciations,
            markup=markup,
            voice_sections=voice_sections,
            chunk=chunk,
            max_chars=max_chars,
            auto_lang=auto_lang,
        )
        if not segments:
            handle_error("No text provided for speech generation", ErrorType.INVALID_INPUT)
        handle_segmented_speech_generation(
            segments=segments,
            tts_provider=tts_provider,
            provider=provider,
            default_voice=voice,
            model=model,
            output=output,
            play_audio=play_audio,
            keep_temp=keep_temp,
            temp_dir=temp_dir,
            volume=volume,
            debug=debug,
            stability=stability,
            similarity_boost=similarity_boost,
            speed=speed,
            response_format=response_format,
            lang=lang,
            instructions=instructions,
            audio_processing=audio_processing,
        )
        if timestamp_output:
            _write_timestamps_for_text(
                timestamp_output, "\n".join(segment.text for segment in segments), timestamp_format
            )
        return

    # Handle repeated stdin generation
    if watch_stdin:
        if sys.stdin.isatty():
            handle_error("--watch-stdin requires piped stdin", ErrorType.INVALID_INPUT)
        count = 0
        for chunk_text in iter_stdin_chunks(sys.stdin):
            count += 1
            console.print(f"[cyan]Processing stdin item {count}...[/cyan]")
            handle_speech_generation(
                text=chunk_text,
                tts_provider=tts_provider,
                provider=provider,
                voice=voice,
                model=model,
                output=None,
                play_audio=play_audio,
                keep_temp=keep_temp,
                temp_dir=temp_dir,
                volume=volume,
                debug=debug,
                stability=stability,
                similarity_boost=similarity_boost,
                speed=speed,
                response_format=response_format,
                lang=lang,
                instructions=instructions,
                audio_processing=audio_processing,
            )
        if count == 0:
            handle_error("No input received from stdin", ErrorType.INVALID_INPUT)
        return

    # Handle speech generation
    if not text:
        handle_error("No text provided for speech generation", ErrorType.INVALID_INPUT)

    handle_speech_generation(
        text=text,
        tts_provider=tts_provider,
        provider=provider,
        voice=voice,
        model=model,
        output=output,
        play_audio=play_audio,
        keep_temp=keep_temp,
        temp_dir=temp_dir,
        volume=volume,
        debug=debug,
        stability=stability,
        similarity_boost=similarity_boost,
        speed=speed,
        response_format=response_format,
        lang=lang,
        instructions=instructions,
        audio_processing=audio_processing,
    )
    if timestamp_output:
        _write_timestamps_for_text(timestamp_output, text, timestamp_format)


if __name__ == "__main__":
    _run_cli()
