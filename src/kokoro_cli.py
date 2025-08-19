#!/usr/bin/env python
"""CLI commands for managing Kokoro ONNX models."""

import sys
from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from src.model_downloader import ModelDownloader

console = Console()
app = typer.Typer(help="Manage Kokoro ONNX TTS models")


@app.command("download")
def download_models(
    force: Annotated[
        bool,
        typer.Option(
            "--force",
            "-f",
            help="Force re-download even if models exist",
        ),
    ] = False,
) -> None:
    """Download Kokoro ONNX model files."""
    try:
        downloader = ModelDownloader()
        model_path, voice_path = downloader.download_models(force=force)

        if not force and downloader.models_exist():
            console.print("[green]✓ Models are already downloaded[/green]")
            console.print(f"Model: {model_path}")
            console.print(f"Voices: {voice_path}")
    except Exception as e:
        console.print(f"[red]Error downloading models: {e}[/red]")
        sys.exit(1)


@app.command("info")
def model_info() -> None:
    """Show information about downloaded models."""
    downloader = ModelDownloader()
    info = downloader.get_model_info()

    console.print("[bold cyan]Kokoro ONNX Model Information[/bold cyan]\n")
    console.print(f"Data directory: [yellow]{info['data_directory']}[/yellow]\n")

    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Model")
    table.add_column("Status")
    table.add_column("Size (MB)")
    table.add_column("Path")

    for name, details in info["models"].items():
        status = "[green]Downloaded[/green]" if details["exists"] else "[red]Not found[/red]"
        size = str(details["size_mb"]) if details["exists"] else "-"
        table.add_row(name.capitalize(), status, size, details["path"])

    console.print(table)

    if not all(m["exists"] for m in info["models"].values()):
        console.print("\n[yellow]Run 'par-tts-kokoro download' to download missing models[/yellow]")


@app.command("clear")
def clear_models(
    confirm: Annotated[
        bool,
        typer.Option(
            "--yes",
            "-y",
            help="Skip confirmation prompt",
        ),
    ] = False,
) -> None:
    """Remove downloaded Kokoro ONNX model files."""
    if not confirm:
        console.print("[yellow]⚠️  This will delete all downloaded Kokoro ONNX models[/yellow]")
        response = typer.prompt("Are you sure? (y/N)", default="n")
        if response.lower() != "y":
            console.print("[dim]Cancelled[/dim]")
            return

    try:
        downloader = ModelDownloader()
        downloader.clear_models()
        console.print("[green]✓ Models cleared successfully[/green]")
    except Exception as e:
        console.print(f"[red]Error clearing models: {e}[/red]")
        sys.exit(1)


@app.command("path")
def show_paths() -> None:
    """Show where models are stored."""
    downloader = ModelDownloader()
    model_path, voice_path = downloader.get_model_paths()

    console.print("[bold cyan]Kokoro ONNX Model Paths[/bold cyan]\n")
    console.print(f"Model:  {model_path}")
    console.print(f"Voices: {voice_path}")

    if downloader.models_exist():
        console.print("\n[green]✓ Both models are present[/green]")
    else:
        console.print("\n[yellow]⚠️  Models not found. Run 'par-tts-kokoro download' to download[/yellow]")


if __name__ == "__main__":
    app()
