"""File-based audio post-processing helpers."""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path

from par_tts.errors import ErrorType, TTSError


@dataclass(frozen=True)
class AudioProcessingOptions:
    """Options for ffmpeg-backed audio post-processing."""

    normalize: bool = False
    trim_silence: bool = False
    preset: str | None = None
    fade_in_ms: int = 0
    fade_out_ms: int = 0

    @property
    def enabled(self) -> bool:
        """Whether any post-processing option is active."""
        return bool(self.normalize or self.trim_silence or self.preset or self.fade_in_ms or self.fade_out_ms)


def build_ffmpeg_postprocess_command(source: Path, target: Path, options: AudioProcessingOptions) -> list[str]:
    """Build a safe ffmpeg argv list for post-processing."""
    filters = _filters_for_options(options)
    command = ["ffmpeg", "-y", "-i", str(source)]
    if filters:
        command.extend(["-af", ",".join(filters)])
    command.append(str(target))
    return command


def concat_audio_files(inputs: list[Path], output: Path) -> None:
    """Concatenate audio files with ffmpeg's concat demuxer."""
    if not inputs:
        raise TTSError("No audio files to concatenate", ErrorType.INVALID_INPUT)
    if shutil.which("ffmpeg") is None:
        raise TTSError("Joining chunked audio output requires ffmpeg to be installed", ErrorType.PROVIDER_ERROR)

    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", suffix=".txt", prefix="par_tts_concat_", delete=False) as list_file:
        list_path = Path(list_file.name)
        for input_path in inputs:
            escaped = str(input_path).replace("'", "'\\''")
            list_file.write(f"file '{escaped}'\n")

    command = ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_path), "-c", "copy", str(output)]
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
    except subprocess.CalledProcessError as e:
        raise TTSError(f"ffmpeg audio join failed: {e.stderr or e}", ErrorType.PROVIDER_ERROR) from e
    finally:
        if list_path.exists():
            list_path.unlink()


def postprocess_audio_file(path: Path, options: AudioProcessingOptions) -> None:
    """Post-process an audio file in place using ffmpeg.

    Args:
        path: Audio file to replace with processed output.
        options: Processing options.

    Raises:
        TTSError: If processing is requested but ffmpeg is unavailable or fails.
    """
    if not options.enabled:
        return
    if shutil.which("ffmpeg") is None:
        raise TTSError("Audio post-processing requires ffmpeg to be installed", ErrorType.PROVIDER_ERROR)

    with tempfile.NamedTemporaryFile(suffix=path.suffix, prefix="par_tts_processed_", delete=False) as tmp:
        temp_path = Path(tmp.name)

    command = build_ffmpeg_postprocess_command(path, temp_path, options)
    try:
        subprocess.run(command, check=True, capture_output=True, text=True)
        temp_path.replace(path)
    except subprocess.CalledProcessError as e:
        if temp_path.exists():
            temp_path.unlink()
        raise TTSError(f"ffmpeg post-processing failed: {e.stderr or e}", ErrorType.PROVIDER_ERROR) from e
    except Exception:
        if temp_path.exists():
            temp_path.unlink()
        raise


def _filters_for_options(options: AudioProcessingOptions) -> list[str]:
    filters: list[str] = []
    preset = (options.preset or "").lower()

    trim_silence = options.trim_silence or preset in {"podcast", "notification"}
    normalize = options.normalize or preset in {"podcast", "notification"}
    fade_in_ms = options.fade_in_ms or (25 if preset == "notification" else 0)
    fade_out_ms = options.fade_out_ms or (75 if preset == "notification" else 0)

    if trim_silence:
        filters.append("silenceremove=start_periods=1:start_duration=0.1:start_threshold=-50dB")
    if preset == "podcast":
        filters.append("highpass=f=80")
    if normalize:
        filters.append("loudnorm=I=-16:TP=-1.5:LRA=11" if preset == "podcast" else "loudnorm")
    if preset in {"podcast", "notification"}:
        filters.append("alimiter=limit=0.95")
    if fade_in_ms > 0:
        filters.append(f"afade=t=in:st=0:d={fade_in_ms / 1000:.3f}")
    if fade_out_ms > 0:
        filters.append(f"afade=t=out:st=0:d={fade_out_ms / 1000:.3f}")
    return filters
