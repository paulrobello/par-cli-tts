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
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any

import typer
from dotenv import load_dotenv
from rich.console import Console
from rich.pretty import Pretty
from rich.table import Table

from src.config_file import ConfigManager
from src.errors import ErrorType, handle_error, validate_api_key, validate_file_path
from src.providers import PROVIDERS, TTSProvider

console = Console()
app = typer.Typer(help="Text-to-speech command line tool with multiple provider support")

# Default configurations
DEFAULT_PROVIDER = "kokoro-onnx"
DEFAULT_ELEVENLABS_VOICE = "Juniper"
DEFAULT_OPENAI_VOICE = "nova"
DEFAULT_KOKORO_VOICE = "af_sarah"


def get_api_key(provider: str) -> str | None:
    """
    Get API key for the specified provider from environment.

    Args:
        provider: Provider name (elevenlabs, openai, kokoro-onnx).

    Returns:
        API key string or None for providers that don't need one.

    Raises:
        SystemExit: If API key is not found in environment.
    """
    # kokoro-onnx doesn't need an API key
    if provider == "kokoro-onnx":
        return None

    env_var_map = {
        "elevenlabs": "ELEVENLABS_API_KEY",
        "openai": "OPENAI_API_KEY",
    }

    env_var = env_var_map.get(provider)
    if not env_var:
        handle_error(f"Unknown provider '{provider}'", ErrorType.INVALID_PROVIDER)
        return None  # For type checker, never reached

    api_key = os.getenv(env_var)
    if not api_key and provider != "kokoro-onnx":
        handle_error(
            f"{env_var} not found. Please set {env_var} in your .env file or environment", ErrorType.MISSING_API_KEY
        )

    return api_key


def get_default_voice(provider: str) -> str:
    """
    Get default voice for the specified provider.

    Args:
        provider: Provider name.

    Returns:
        Default voice ID for the provider.
    """
    defaults = {
        "elevenlabs": os.getenv("ELEVENLABS_VOICE_ID", DEFAULT_ELEVENLABS_VOICE),
        "openai": os.getenv("OPENAI_VOICE_ID", DEFAULT_OPENAI_VOICE),
        "kokoro-onnx": os.getenv("KOKORO_VOICE_ID", DEFAULT_KOKORO_VOICE),
    }
    return defaults.get(provider, "")


def create_provider(provider_name: str, **kwargs: Any) -> TTSProvider:
    """
    Create a TTS provider instance.

    Args:
        provider_name: Name of the provider.
        **kwargs: Additional provider configuration.

    Returns:
        Initialized TTS provider.

    Raises:
        SystemExit: If provider is not found or cannot be initialized.
    """
    if provider_name not in PROVIDERS:
        handle_error(
            f"Unknown provider '{provider_name}'. Available: {', '.join(PROVIDERS.keys())}", ErrorType.INVALID_PROVIDER
        )

    api_key = get_api_key(provider_name)
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
        raise  # Re-raise for type checker


@app.command()
def main(
    text: Annotated[
        str | None, typer.Argument(help="Text to convert to speech. Use '-' for stdin, '@filename' to read from file")
    ] = None,
    provider: Annotated[
        str,
        typer.Option(
            "-P",
            "--provider",
            help="TTS provider to use (elevenlabs, openai, kokoro-onnx)",
            envvar="TTS_PROVIDER",
        ),
    ] = DEFAULT_PROVIDER,
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
        float,
        typer.Option(
            "-s",
            "--stability",
            help="Voice stability for ElevenLabs (0.0 to 1.0)",
            min=0.0,
            max=1.0,
        ),
    ] = 0.5,
    similarity_boost: Annotated[
        float,
        typer.Option(
            "-S",
            "--similarity",
            help="Voice similarity boost for ElevenLabs (0.0 to 1.0)",
            min=0.0,
            max=1.0,
        ),
    ] = 0.5,
    speed: Annotated[
        float,
        typer.Option(
            "-r",
            "--speed",
            help="Speech speed for OpenAI/Kokoro (0.25 to 4.0)",
            min=0.25,
            max=4.0,
        ),
    ] = 1.0,
    response_format: Annotated[
        str,
        typer.Option(
            "-f",
            "--format",
            help="Audio format for OpenAI (mp3, opus, aac, flac, wav)",
        ),
    ] = "mp3",
    lang: Annotated[
        str,
        typer.Option(
            "-g",
            "--lang",
            help="Language code for Kokoro ONNX (e.g., en-us)",
        ),
    ] = "en-us",
    volume: Annotated[
        float,
        typer.Option(
            "-w",
            "--volume",
            help="Playback volume (0.0 = silent, 1.0 = normal, 2.0 = double)",
            min=0.0,
            max=5.0,
        ),
    ] = 1.0,
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
) -> None:
    """
    Convert text to speech using various TTS providers.

    This tool accepts text as input and converts it to speech using the
    specified TTS provider. Voices can be configured via command line options
    or environment variables.
    """
    load_dotenv()

    # Handle create config first
    if create_config:
        config_manager = ConfigManager()
        config_manager.create_sample_config()
        return

    # Load configuration file
    config_manager = ConfigManager()
    config_file = config_manager.load_config()

    # Apply config file defaults (CLI args override these)
    if config_file:
        # Update defaults from config file
        provider = provider or config_file.provider or DEFAULT_PROVIDER
        voice = voice or config_file.voice
        model = model or config_file.model
        output = output or (Path(config_file.output_dir) / "output.mp3" if config_file.output_dir else None)
        response_format = response_format if response_format != "mp3" else config_file.output_format or "mp3"
        keep_temp = keep_temp if keep_temp else config_file.keep_temp or False
        temp_dir = temp_dir or (Path(config_file.temp_dir) if config_file.temp_dir else None)
        volume = volume if volume != 1.0 else config_file.volume or 1.0
        speed = speed if speed != 1.0 else config_file.speed or 1.0
        stability = stability if stability != 0.5 else config_file.stability or 0.5
        similarity_boost = similarity_boost if similarity_boost != 0.5 else config_file.similarity_boost or 0.5
        lang = lang or config_file.lang or "en-us"
        play_audio = (
            play_audio if play_audio else config_file.play_audio if config_file.play_audio is not None else True
        )
        debug = debug or config_file.debug or False

    # Store debug mode globally for error handler
    sys._debug_mode = debug  # type: ignore

    # Check if text is required (not needed for certain operations)
    text_required = not (
        list_providers or list_voices or preview_voice or dump_config or refresh_cache or clear_cache_samples
    )

    # Automatically read from stdin if no text provided and stdin has data
    if text_required and text is None:
        # Check if stdin has data
        if sys.stdin.isatty():
            # No piped input, show error
            handle_error(
                "TEXT argument is required. Use --help for more information. You can also pipe text: echo 'text' | par-tts",
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
        # Read from file
        file_path = Path(text[1:])
        validate_file_path(str(file_path), must_exist=True)
        try:
            with open(file_path, encoding="utf-8") as f:
                text = f.read()
            if not text:
                handle_error(f"File '{file_path}' is empty", ErrorType.INVALID_INPUT)
        except Exception as e:
            handle_error(f"Failed to read file '{file_path}'", ErrorType.FILE_NOT_FOUND, exception=e)

    # Handle list providers
    if list_providers:
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
        return

    # Create provider
    tts_provider = create_provider(provider)

    # Handle cache management operations (ElevenLabs only)
    if refresh_cache or clear_cache_samples:
        if provider == "elevenlabs":
            from src.providers.elevenlabs import ElevenLabsProvider
            from src.voice_cache import VoiceCache

            if isinstance(tts_provider, ElevenLabsProvider):
                cache = VoiceCache("par-tts-elevenlabs")

                if refresh_cache:
                    console.print("[cyan]Force refreshing voice cache...[/cyan]")
                    if cache.refresh_cache(tts_provider.client):
                        console.print("[green]✓ Voice cache refreshed successfully[/green]")
                    else:
                        console.print("[yellow]Voice cache is already up to date[/yellow]")

                if clear_cache_samples:
                    console.print("[cyan]Clearing cached voice samples...[/cyan]")
                    cache.clear_cache(keep_samples=False)
                    console.print("[green]✓ Voice samples cleared[/green]")

                return
        else:
            console.print("[yellow]Cache management is only available for ElevenLabs provider[/yellow]")
            return

    # Handle list voices
    if list_voices:
        console.print(f"[bold green]Available Voices for {tts_provider.name}:[/bold green]")
        try:
            voices = tts_provider.list_voices()
            for v in voices:
                labels_str = ", ".join(v.labels) if v.labels else "No labels"
                console.print(f"  [yellow]{v.id}[/yellow]: [white]{v.name}[/white] - {labels_str}")
        except Exception as e:
            handle_error("Failed to fetch available voices", ErrorType.PROVIDER_ERROR, exception=e)
        return

    # Handle voice preview
    if preview_voice:
        console.print(f"[bold cyan]Previewing voice: {preview_voice}[/bold cyan]")
        sample_text = "Hello! This is a preview of the voice you selected. The quick brown fox jumps over the lazy dog."

        try:
            # Resolve voice
            resolved_voice = tts_provider.resolve_voice(preview_voice)
            console.print(f"[dim]Voice resolved to: {resolved_voice}[/dim]")

            # Check for cached sample first (ElevenLabs only)
            audio_data = None
            if provider == "elevenlabs":
                from src.voice_cache import VoiceCache

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
                    from src.voice_cache import VoiceCache

                    cache = VoiceCache("par-tts-elevenlabs")
                    cache.cache_voice_sample(resolved_voice, sample_text, audio_data)

            # Play the preview
            console.print("[cyan]Playing preview...[/cyan]")
            tts_provider.play_audio(audio_data, volume=volume)

            console.print("[green]✓ Preview complete![/green]")
        except Exception as e:
            handle_error("Failed to preview voice", ErrorType.PROVIDER_ERROR, exception=e)
        return

    # Get default voice if not specified
    if not voice:
        voice = get_default_voice(provider)
        if not voice:
            voice = tts_provider.default_voice

    # Handle dump config
    if dump_config:
        config = {
            "provider": provider,
            "voice": voice,
            "model": model or tts_provider.default_model,
            "output": str(output) if output else None,
            "play_audio": play_audio,
            "keep_temp": keep_temp,
            "temp_dir": str(temp_dir) if temp_dir else None,
        }

        # Add provider-specific config
        if provider == "elevenlabs":
            config.update(
                {
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                }
            )
        elif provider == "openai":
            config.update(
                {
                    "speed": speed,
                    "response_format": response_format,
                }
            )
        elif provider == "kokoro-onnx":
            config.update(
                {
                    "speed": speed,
                    "lang": lang,
                }
            )

        console.print("[bold cyan]Configuration:[/bold cyan]")
        console.print(Pretty(config))

        # Show config file info
        if config_file:
            console.print(f"\n[dim]Config file loaded from: {config_manager.config_file}[/dim]")
        else:
            console.print(f"\n[dim]No config file found at: {config_manager.config_file}[/dim]")
            console.print("[dim]Use --create-config to create a sample configuration file[/dim]")

        return

    # Resolve voice
    try:
        original_voice = voice
        voice = tts_provider.resolve_voice(voice)
        if debug and original_voice != voice:
            console.print(f"[dim]Resolved '{original_voice}' to voice ID: {voice}[/dim]")
    except ValueError as e:
        handle_error(str(e), ErrorType.INVALID_VOICE, exception=e)

    # Debug information
    if debug:
        from src.utils import sanitize_debug_output

        # Create debug info dict
        debug_info = {
            "Provider": provider,
            "Text_length": f"{len(text)} characters" if text else "N/A",
            "Voice_input": original_voice,
            "Voice_ID": voice,
            "Model": model or "default",
        }

        # Add environment variables (sanitized)
        env_vars = {}
        for key in os.environ:
            if "API" in key or "KEY" in key or "TOKEN" in key or "TTS" in key:
                env_vars[key] = os.environ[key]

        sanitized_env = sanitize_debug_output(env_vars)

        console.print("[bold cyan]Debug Information:[/bold cyan]")
        for key, value in debug_info.items():
            console.print(f"  {key}: {value}")

        # Show sanitized environment variables if any are relevant
        if env_vars:
            console.print("\n[bold cyan]Environment Variables (sanitized):[/bold cyan]")
            for key, value in sanitized_env.items():
                console.print(f"  {key}: {value}")

        # Add additional debug info
        console.print(f"  Output_file: {output or 'None'}")
        console.print(f"  Play_audio: {play_audio}")
        if temp_dir:
            console.print(f"  Temp directory: {temp_dir}")
        console.print()

    try:
        console.print("[cyan]Generating speech...[/cyan]")

        # Prepare provider-specific parameters
        kwargs = {}
        if provider == "elevenlabs":
            kwargs.update(
                {
                    "stability": stability,
                    "similarity_boost": similarity_boost,
                }
            )
        elif provider == "openai":
            kwargs.update(
                {
                    "speed": speed,
                    "response_format": response_format,
                }
            )
        elif provider == "kokoro-onnx":
            kwargs.update(
                {
                    "speed": speed,
                    "lang": lang,
                }
            )

        # Generate speech
        if not text:
            handle_error("No text provided for speech generation", ErrorType.INVALID_INPUT)
            return  # For type checker

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
            console.print(f"[green]✓ Audio saved to: {output_path}[/green]")

            if play_audio:
                console.print("[cyan]Playing audio...[/cyan]")
                tts_provider.play_audio(audio_data, volume=volume)
        else:
            if play_audio:
                console.print("[cyan]Playing audio...[/cyan]")
                # Generate filename with timestamp if needed
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"tts_{timestamp}.mp3"

                # Create temp file in specified directory or system temp
                if temp_dir:
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    tmp_path = temp_dir / filename
                else:
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                        tmp_path = Path(tmp.name)

                tts_provider.save_audio(audio_data, tmp_path)

                try:
                    tts_provider.play_audio(audio_data, volume=volume)

                    if keep_temp or temp_dir:
                        console.print(f"[green]✓ Audio saved to: {tmp_path}[/green]")
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
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"tts_{timestamp}.mp3"

                if temp_dir:
                    temp_dir.mkdir(parents=True, exist_ok=True)
                    tmp_path = temp_dir / filename
                else:
                    with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as tmp:
                        tmp_path = Path(tmp.name)

                tts_provider.save_audio(audio_data, tmp_path)
                console.print(f"[green]✓ Audio saved to: {tmp_path}[/green]")
                if temp_dir:
                    console.print(f"[dim]Saved in specified directory: {temp_dir}[/dim]")
                else:
                    console.print("[dim]File saved in system temp directory[/dim]")

        console.print("[green]✓ Speech generation complete![/green]")

    except Exception as e:
        # Store debug mode for error handler
        sys._debug_mode = debug  # type: ignore
        handle_error("Failed to generate speech", ErrorType.PROVIDER_ERROR, exception=e)


if __name__ == "__main__":
    app()
