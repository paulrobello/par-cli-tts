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

from src.providers import PROVIDERS, TTSProvider

console = Console()
app = typer.Typer(help="Text-to-speech command line tool with multiple provider support")

# Default configurations
DEFAULT_PROVIDER = "elevenlabs"
DEFAULT_ELEVENLABS_VOICE = "aMSt68OGf4xUZAnLpTU8"
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
        console.print(f"[red]Error: Unknown provider '{provider}'[/red]")
        sys.exit(1)

    api_key = os.getenv(env_var)
    if not api_key:
        console.print(f"[red]Error: {env_var} not found in environment[/red]")
        console.print(f"Please set {env_var} in your .env file or environment")
        sys.exit(1)

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
        console.print(f"[red]Error: Unknown provider '{provider_name}'[/red]")
        console.print(f"Available providers: {', '.join(PROVIDERS.keys())}")
        sys.exit(1)

    api_key = get_api_key(provider_name)
    provider_class = PROVIDERS[provider_name]

    try:
        if provider_name == "kokoro-onnx":
            # kokoro-onnx doesn't use API key
            return provider_class(**kwargs)
        else:
            return provider_class(api_key, **kwargs)
    except Exception as e:
        console.print(f"[red]Error initializing {provider_name} provider: {e}[/red]")
        sys.exit(1)


@app.command()
def main(
    text: Annotated[str, typer.Argument(help="Text to convert to speech")],
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
            "--speed",
            help="Speech speed for OpenAI (0.25 to 4.0)",
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
            "--lang",
            help="Language code for Kokoro ONNX (e.g., en-us)",
        ),
    ] = "en-us",
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
) -> None:
    """
    Convert text to speech using various TTS providers.

    This tool accepts text as input and converts it to speech using the
    specified TTS provider. Voices can be configured via command line options
    or environment variables.
    """
    load_dotenv()

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

    # Handle list voices
    if list_voices:
        console.print(f"[bold green]Available Voices for {tts_provider.name}:[/bold green]")
        try:
            voices = tts_provider.list_voices()
            for v in voices:
                labels_str = ", ".join(v.labels) if v.labels else "No labels"
                console.print(f"  [yellow]{v.id}[/yellow]: [white]{v.name}[/white] - {labels_str}")
        except Exception as e:
            console.print(f"[red]Error fetching voices: {e}[/red]")
            sys.exit(1)
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
        return

    # Resolve voice
    try:
        original_voice = voice
        voice = tts_provider.resolve_voice(voice)
        if debug and original_voice != voice:
            console.print(f"[dim]Resolved '{original_voice}' to voice ID: {voice}[/dim]")
    except ValueError as e:
        console.print(f"[red]Error: {e}[/red]")
        sys.exit(1)

    # Debug information
    if debug:
        console.print("[bold cyan]Debug Information:[/bold cyan]")
        console.print(f"  Provider: {provider}")
        console.print(f"  Text length: {len(text)} characters")
        console.print(f"  Voice input: {original_voice}")
        console.print(f"  Voice ID: {voice}")
        console.print(f"  Model: {model or tts_provider.default_model}")
        console.print(f"  Output file: {output}")
        console.print(f"  Play audio: {play_audio}")
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
                tts_provider.play_audio(audio_data)
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
                    tts_provider.play_audio(audio_data)

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
        console.print(f"[red]Error generating speech: {e}[/red]")
        if debug:
            import traceback

            console.print("[red]" + traceback.format_exc() + "[/red]")
        sys.exit(1)


if __name__ == "__main__":
    app()
