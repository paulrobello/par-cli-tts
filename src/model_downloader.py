"""Model downloader for Kokoro ONNX TTS models."""

import urllib.error
import urllib.request
from pathlib import Path

from platformdirs import user_data_dir
from rich.console import Console
from rich.progress import BarColumn, DownloadColumn, Progress, SpinnerColumn, TextColumn, TransferSpeedColumn

console = Console()


class ModelDownloader:
    """Downloads and manages Kokoro ONNX model files."""

    # Model URLs and metadata
    # Using the quantized int8 version for smaller download size
    MODELS = {
        "kokoro-v1.0.onnx": {
            "url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx",
            "size_mb": 88,  # Approximate size in MB
            "sha256": None,  # Could add hash verification if available
            "filename": "kokoro-v1.0.onnx",  # Save as standard name
        },
        "voices-v1.0.bin": {
            "url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
            "size_mb": 18,  # Approximate size in MB
            "sha256": None,
            "filename": "voices-v1.0.bin",
        },
    }

    def __init__(self):
        """Initialize the model downloader."""
        # Use XDG-compliant data directory
        self.data_dir = Path(user_data_dir("par-tts-kokoro", "par-tts"))
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_model_paths(self) -> tuple[Path, Path]:
        """Get the paths where models are/will be stored.

        Returns:
            Tuple of (model_path, voice_path)
        """
        model_path = self.data_dir / "kokoro-v1.0.onnx"
        voice_path = self.data_dir / "voices-v1.0.bin"
        return model_path, voice_path

    def models_exist(self) -> bool:
        """Check if both model files exist.

        Returns:
            True if both files exist, False otherwise.
        """
        model_path, voice_path = self.get_model_paths()
        return model_path.exists() and voice_path.exists()

    def _download_file(self, url: str, dest_path: Path, description: str, size_mb: int) -> None:
        """Download a file with progress indication.

        Args:
            url: URL to download from.
            dest_path: Destination file path.
            description: Description for progress bar.
            size_mb: Approximate size in MB for display.
        """
        try:
            # Create a temporary file first
            temp_path = dest_path.with_suffix(".tmp")

            with Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                DownloadColumn(),
                TransferSpeedColumn(),
                console=console,
            ) as progress:
                # Start the download task
                task = progress.add_task(description, total=None)

                def download_hook(block_num: int, block_size: int, total_size: int) -> None:
                    """Hook for urllib to update progress."""
                    if total_size > 0:
                        # Update total if we know it
                        if progress.tasks[task].total is None:
                            progress.update(task, total=total_size)
                        # Update progress
                        downloaded = block_num * block_size
                        progress.update(task, completed=min(downloaded, total_size))

                # Download the file
                urllib.request.urlretrieve(url, temp_path, reporthook=download_hook)

                # Move temp file to final destination
                temp_path.rename(dest_path)

        except urllib.error.URLError as e:
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"Failed to download {description}: {e}")
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"Download error: {e}")

    def download_models(self, force: bool = False) -> tuple[Path, Path]:
        """Download Kokoro ONNX model files if needed.

        Args:
            force: Force re-download even if files exist.

        Returns:
            Tuple of (model_path, voice_path)
        """
        model_path, voice_path = self.get_model_paths()

        # Check if we need to download
        if not force and self.models_exist():
            return model_path, voice_path

        # Inform user about download
        console.print("\n[bold cyan]🤖 Kokoro ONNX Model Download Required[/bold cyan]")
        console.print(f"Models will be downloaded to: [yellow]{self.data_dir}[/yellow]\n")

        total_size = sum(m["size_mb"] for m in self.MODELS.values())
        console.print(
            f"[dim]Total download size: approximately {total_size} MB (using quantized model for efficiency)[/dim]\n"
        )

        # Download model file if needed
        if force or not model_path.exists():
            model_info = self.MODELS["kokoro-v1.0.onnx"]
            console.print(f"📥 Downloading ONNX model ([cyan]~{model_info['size_mb']} MB[/cyan])...")
            self._download_file(model_info["url"], model_path, "kokoro-v1.0.onnx", model_info["size_mb"])
            console.print(f"[green]✓[/green] Model downloaded: {model_path.name}\n")
        else:
            console.print(f"[green]✓[/green] Model already exists: {model_path.name}")

        # Download voice file if needed
        if force or not voice_path.exists():
            voice_info = self.MODELS["voices-v1.0.bin"]
            console.print(f"📥 Downloading voice embeddings ([cyan]~{voice_info['size_mb']} MB[/cyan])...")
            self._download_file(voice_info["url"], voice_path, "voices-v1.0.bin", voice_info["size_mb"])
            console.print(f"[green]✓[/green] Voices downloaded: {voice_path.name}\n")
        else:
            console.print(f"[green]✓[/green] Voices already exist: {voice_path.name}")

        console.print("[bold green]✨ Kokoro ONNX models ready![/bold green]\n")
        console.print(f"[dim]Model files stored in: {self.data_dir}[/dim]\n")

        return model_path, voice_path

    def clear_models(self) -> None:
        """Remove downloaded model files."""
        model_path, voice_path = self.get_model_paths()

        if model_path.exists():
            model_path.unlink()
            console.print(f"[yellow]Removed:[/yellow] {model_path.name}")

        if voice_path.exists():
            voice_path.unlink()
            console.print(f"[yellow]Removed:[/yellow] {voice_path.name}")

        # Remove directory if empty
        try:
            self.data_dir.rmdir()
            console.print(f"[yellow]Removed:[/yellow] {self.data_dir}")
        except OSError:
            # Directory not empty, that's fine
            pass

    def get_model_info(self) -> dict:
        """Get information about model files.

        Returns:
            Dictionary with model file information.
        """
        model_path, voice_path = self.get_model_paths()

        info = {"data_directory": str(self.data_dir), "models": {}}

        for name, path in [("model", model_path), ("voices", voice_path)]:
            if path.exists():
                stat = path.stat()
                info["models"][name] = {
                    "path": str(path),
                    "size_mb": round(stat.st_size / (1024 * 1024), 2),
                    "exists": True,
                }
            else:
                info["models"][name] = {"path": str(path), "size_mb": 0, "exists": False}

        return info
