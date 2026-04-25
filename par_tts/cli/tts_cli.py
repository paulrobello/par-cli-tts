#!/usr/bin/env python
"""
Command line tool for text-to-speech using multiple TTS providers.

This module provides a CLI interface for converting text to speech using
various TTS providers (ElevenLabs, OpenAI, etc). It supports configurable
voices, multiple providers, and various output options.
"""

import os
import sys
import tempfile
from pathlib import Path
from typing import Annotated, Any

import typer
from dotenv import load_dotenv
from rich.pretty import Pretty
from rich.table import Table

from par_tts.cli.config_file import ConfigManager
from par_tts.cli.console import console
from par_tts.defaults import DEFAULT_PROVIDER, get_default_voice
from par_tts.errors import ErrorType, TTSError, handle_error, set_debug_mode, validate_api_key, validate_file_path
from par_tts.providers import PROVIDERS, TTSProvider

app = typer.Typer(help="Text-to-speech command line tool with multiple provider support")


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


def get_api_key(provider: str, config_file: Any = None) -> str | None:
    """
    Get API key for the specified provider from config file or environment.

    Args:
        provider: Provider name (elevenlabs, openai, kokoro-onnx, deepgram, gemini).
        config_file: Optional config file with API keys.

    Returns:
        API key string or None for providers that don't need one.

    Raises:
        TTSError: If API key is not found anywhere.
    """
    # kokoro-onnx doesn't need an API key
    if provider == "kokoro-onnx":
        return None

    # Map provider to config file field and accepted environment variables (in
    # priority order). Deepgram historically used DG_API_KEY; Gemini accepts the
    # generic GOOGLE_API_KEY as well as GEMINI_API_KEY.
    key_map: dict[str, tuple[str, ...]] = {
        "elevenlabs": ("elevenlabs_api_key", "ELEVENLABS_API_KEY"),
        "openai": ("openai_api_key", "OPENAI_API_KEY"),
        "deepgram": ("deepgram_api_key", "DEEPGRAM_API_KEY", "DG_API_KEY"),
        "gemini": ("gemini_api_key", "GEMINI_API_KEY", "GOOGLE_API_KEY"),
    }

    if provider not in key_map:
        handle_error(f"Unknown provider '{provider}'", ErrorType.INVALID_PROVIDER)

    config_field, *env_vars = key_map[provider]

    # Check config file first
    if config_file:
        api_key = getattr(config_file, config_field, None)
        if api_key:
            return api_key

    # Fall back to environment variable(s) — first hit wins
    for env_var in env_vars:
        api_key = os.getenv(env_var)
        if api_key:
            return api_key

    primary = env_vars[0]
    alt = f" (also accepts {', '.join(env_vars[1:])})" if len(env_vars) > 1 else ""
    handle_error(
        f"{primary} not found. Please set {primary}{alt} in your config file or environment",
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
    if provider_name not in PROVIDERS:
        handle_error(
            f"Unknown provider '{provider_name}'. Available: {', '.join(PROVIDERS.keys())}", ErrorType.INVALID_PROVIDER
        )

    api_key = get_api_key(provider_name, config_file)
    validate_api_key(api_key, provider_name)
    provider_class = PROVIDERS[provider_name]

    try:
        if provider_name == "kokoro-onnx":
            # kokoro-onnx doesn't use API key
            return provider_class(**kwargs)
        else:
            return provider_class(api_key, **kwargs)
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
) -> None:
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
                console.print(f"[green]Audio saved to: {tmp_path}[/green]")
                if temp_dir:
                    console.print(f"[dim]Saved in specified directory: {temp_dir}[/dim]")
                else:
                    console.print("[dim]File saved in system temp directory[/dim]")

        console.print("[green]Speech generation complete![/green]")

    except Exception as e:
        # Store debug mode for error handler
        set_debug_mode(debug)
        handle_error("Failed to generate speech", ErrorType.PROVIDER_ERROR, exception=e)


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
    # Utility options
    debug: Annotated[
        bool,
        typer.Option(
            "-d",
            "--debug",
            help="Show debug information",
        ),
    ] = False,
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
    dump_config: Annotated[
        bool,
        typer.Option(
            "-D",
            "--dump",
            help="Dump configuration and exit",
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
    load_dotenv()

    # Handle config operations
    config_manager = ConfigManager()
    if handle_config_operations(create_config, config_manager, force=yes):
        return

    # Load configuration file
    config_file = config_manager.load_config()

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
        debug = debug or config_file.debug or False

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

    # Apply default provider if still not set
    if not provider:
        provider = DEFAULT_PROVIDER

    # Store debug mode globally for error handler
    set_debug_mode(debug)

    # Check if text is required (not needed for certain operations)
    text_required = not (
        list_providers
        or list_voices
        or preview_voice
        or dump_config
        or refresh_cache
        or clear_cache_samples
        or clear_kokoro_models
    )

    # Handle input operations
    text = handle_input_operations(text, text_required)

    # Handle list providers
    if list_providers:
        handle_list_providers()
        return

    # Create provider
    tts_provider = create_provider(provider, config_file)

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
            config_file,
            config_manager,
            tts_provider,
        )
        return

    # Resolve voice
    original_voice = voice
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
    )


if __name__ == "__main__":
    _run_cli()
