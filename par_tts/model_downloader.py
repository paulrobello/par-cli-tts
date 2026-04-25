"""Model downloader for Kokoro ONNX TTS models."""

import logging
import urllib.error
import urllib.request
from pathlib import Path

from platformdirs import user_data_dir

from par_tts.utils import verify_file_checksum

_logger = logging.getLogger(__name__)


class ModelDownloader:
    """Downloads and manages Kokoro ONNX model files."""

    # Model URLs and metadata
    # Using the quantized int8 version for smaller download size
    MODELS = {
        "kokoro-v1.0.onnx": {
            "url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/kokoro-v1.0.int8.onnx",
            "size_mb": 88,  # Approximate size in MB
            "sha256": "6e742170d309016e5891a994e1ce1559c702a2ccd0075e67ef7157974f6406cb",
            "filename": "kokoro-v1.0.onnx",  # Save as standard name
        },
        "voices-v1.0.bin": {
            "url": "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/voices-v1.0.bin",
            "size_mb": 18,  # Approximate size in MB
            "sha256": "bca610b8308e8d99f32e6fe4197e7ec01679264efed0cac9140fe9c29f1fbf7d",
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

    def _download_file(
        self, url: str, dest_path: Path, description: str, size_mb: int, sha256: str | None = None
    ) -> None:
        """Download a file with optional checksum verification.

        Args:
            url: URL to download from.
            dest_path: Destination file path.
            description: Description for logging.
            size_mb: Approximate size in MB for display.
            sha256: Optional SHA256 checksum for verification.
        """
        temp_path = dest_path.with_suffix(".tmp")
        try:
            _logger.info("Downloading %s (~%d MB)...", description, size_mb)
            urllib.request.urlretrieve(url, temp_path)

            if sha256:
                _logger.info("Verifying checksum...")
                if not verify_file_checksum(temp_path, sha256):
                    temp_path.unlink()
                    raise RuntimeError(f"Checksum verification failed for {description}")
                _logger.info("Checksum verified")

            temp_path.rename(dest_path)

        except urllib.error.URLError as e:
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"Failed to download {description}: {e}") from e
        except Exception as e:
            if temp_path.exists():
                temp_path.unlink()
            raise RuntimeError(f"Download error: {e}") from e

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

        _logger.info("Kokoro ONNX Model Download Required")
        _logger.info("Models will be downloaded to: %s", self.data_dir)

        total_size = sum(m["size_mb"] for m in self.MODELS.values())
        _logger.info("Total download size: approximately %d MB (using quantized model for efficiency)", total_size)

        # Download model file if needed
        if force or not model_path.exists():
            model_info = self.MODELS["kokoro-v1.0.onnx"]
            _logger.info("Downloading ONNX model (~%d MB)...", model_info["size_mb"])
            self._download_file(
                model_info["url"], model_path, "kokoro-v1.0.onnx", model_info["size_mb"], model_info.get("sha256")
            )
            _logger.info("Model downloaded: %s", model_path.name)
        else:
            _logger.info("Model already exists: %s", model_path.name)

        # Download voice file if needed
        if force or not voice_path.exists():
            voice_info = self.MODELS["voices-v1.0.bin"]
            _logger.info("Downloading voice embeddings (~%d MB)...", voice_info["size_mb"])
            self._download_file(
                voice_info["url"], voice_path, "voices-v1.0.bin", voice_info["size_mb"], voice_info.get("sha256")
            )
            _logger.info("Voices downloaded: %s", voice_path.name)
        else:
            _logger.info("Voices already exist: %s", voice_path.name)

        _logger.info("Kokoro ONNX models ready!")
        _logger.info("Model files stored in: %s", self.data_dir)

        return model_path, voice_path

    def clear_models(self) -> None:
        """Remove downloaded model files."""
        model_path, voice_path = self.get_model_paths()

        if model_path.exists():
            model_path.unlink()
            _logger.info("Removed: %s", model_path.name)

        if voice_path.exists():
            voice_path.unlink()
            _logger.info("Removed: %s", voice_path.name)

        # Remove directory if empty
        try:
            self.data_dir.rmdir()
            _logger.info("Removed: %s", self.data_dir)
        except OSError:
            # Directory not empty, that's fine
            pass

    def get_model_info(self) -> dict:
        """Get information about model files.

        Returns:
            Dictionary with model file information.
        """
        model_path, voice_path = self.get_model_paths()

        info: dict = {"data_directory": str(self.data_dir), "models": {}}

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
