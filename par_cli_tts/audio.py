"""Audio playback utilities."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def play_audio_with_player(file_path: Path, volume: float = 1.0) -> None:
    """Play audio using system player with volume support.

    This function detects the operating system and uses the appropriate
    audio player with volume control support.

    Args:
        file_path: Path to the audio file to play.
        volume: Volume level (0.0 = silent, 1.0 = normal, 2.0 = double).

    Raises:
        RuntimeError: If no suitable audio player is found on Linux.
    """
    if sys.platform == "darwin":  # macOS
        # afplay supports volume flag (-v)
        subprocess.run(["afplay", "-v", str(volume), str(file_path)], check=True)
    elif sys.platform == "win32":  # Windows
        _play_audio_windows(file_path, volume)
    else:  # Linux and others
        # Try common audio players with volume support
        players_with_volume = [
            ("paplay", ["--volume", str(int(volume * 65536))]),  # paplay uses 0-65536
            ("ffplay", ["-volume", str(int(volume * 100)), "-nodisp", "-autoexit"]),  # ffplay uses 0-100
            ("mpg123", ["-f", str(int(volume * 32768))]),  # mpg123 uses scale factor
            ("aplay", []),  # aplay doesn't support volume directly
        ]

        for player, volume_args in players_with_volume:
            try:
                cmd = [player] + volume_args + [str(file_path)]
                subprocess.run(cmd, check=True)
                return
            except (subprocess.CalledProcessError, FileNotFoundError):
                continue

        raise RuntimeError("No audio player found. Install aplay, paplay, ffplay, or mpg123.")


def _find_windows_audio_player() -> str | None:
    """Find an available audio player on Windows.

    Checks for ffplay, VLC, and mpg123 in that order.

    Returns:
        Name of the found player, or None if no player is available.
    """
    # Prefer ffplay (comes with ffmpeg, most reliable)
    if shutil.which("ffplay"):
        return "ffplay"

    # VLC media player
    vlc_paths = [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
    ]
    for vlc_path in vlc_paths:
        if Path(vlc_path).exists():
            return "vlc"

    # mpg123 for Windows
    if shutil.which("mpg123"):
        return "mpg123"

    return None


def _play_with_powershell(file_path: Path, volume: float, timeout: int = 60) -> None:
    """Play audio using PowerShell MediaPlayer COM object.

    This is a fallback for Windows when no external player is available.
    Uses the Windows built-in MediaPlayer COM object for reliable playback.

    Args:
        file_path: Path to the audio file to play.
        volume: Volume level (0.0 = silent, 1.0 = normal, 2.0 = double).
            Note: MediaPlayer volume range is 0.0 to 1.0, values above 1.0
            are capped at 1.0.
        timeout: Maximum playback time in seconds.

    Raises:
        RuntimeError: If PowerShell execution fails.
    """
    # MediaPlayer volume is 0.0 to 1.0, cap values above 1.0
    media_volume = min(volume, 1.0)

    # PowerShell script using MediaPlayer COM object
    ps_script = f"""
$file = "{file_path}"
$volume = {media_volume}

$player = New-Object -ComObject MediaPlayer.MediaPlayer
$player.Open($file)
$player.Volume = $volume

# Wait for media to be ready
while ($player.ReadyState -lt 3) {{
    Start-Sleep -Milliseconds 100
}}

# Get duration and wait for playback
$duration = $player.Duration
if ($duration -gt 0) {{
    $player.Play()
    Start-Sleep -Seconds $duration
}} else {{
    # If duration not available, wait up to {timeout} seconds
    $player.Play()
    Start-Sleep -Seconds {timeout}
}}

$player.Close()
[System.Runtime.InteropServices.Marshal]::ReleaseComObject($player) | Out-Null
"""

    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            check=True,
            timeout=timeout + 10,  # Extra buffer for startup/shutdown
        )
    except subprocess.TimeoutExpired as e:
        raise RuntimeError(f"Audio playback timed out after {timeout} seconds") from e
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"PowerShell audio playback failed: {e}") from e


def _play_audio_windows(file_path: Path, volume: float = 1.0) -> None:
    """Play audio on Windows with volume control.

    Tries external players first (ffplay, VLC, mpg123), then falls back
    to PowerShell MediaPlayer COM object.

    Args:
        file_path: Path to the audio file to play.
        volume: Volume level (0.0 = silent, 1.0 = normal, 2.0 = double).

    Raises:
        RuntimeError: If no audio playback method succeeds.
    """
    player = _find_windows_audio_player()

    if player == "ffplay":
        # ffplay uses 0-100 volume scale
        subprocess.run(
            [
                "ffplay",
                "-volume",
                str(int(volume * 100)),
                "-nodisp",
                "-autoexit",
                "-hide_banner",
                "-loglevel",
                "error",
                str(file_path),
            ],
            check=True,
        )
    elif player == "vlc":
        # VLC volume scale: 0-256 where 256 is 100%
        # Higher values possible but 512 is 200%
        vlc_path = r"C:\Program Files\VideoLAN\VLC\vlc.exe"
        if not Path(vlc_path).exists():
            vlc_path = r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe"
        subprocess.run(
            [
                vlc_path,
                "--intf",
                "dummy",
                "--play-and-exit",
                "--volume",
                str(int(volume * 256)),
                str(file_path),
            ],
            check=True,
        )
    elif player == "mpg123":
        # mpg123 uses scale factor (32768 = normal)
        subprocess.run(
            ["mpg123", "-f", str(int(volume * 32768)), str(file_path)],
            check=True,
        )
    else:
        # Fallback to PowerShell MediaPlayer
        _play_with_powershell(file_path, volume)


def play_audio_bytes(audio_data: bytes, volume: float = 1.0, suffix: str = ".mp3") -> None:
    """Play audio data from bytes using system player.

    This is a convenience function that saves audio bytes to a temporary
    file and plays it using the system audio player.

    Args:
        audio_data: Audio data as bytes.
        volume: Volume level (0.0 = silent, 1.0 = normal, 2.0 = double).
        suffix: File suffix for temporary file (default: .mp3).
    """
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_data)
        tmp_path = Path(tmp.name)

    try:
        play_audio_with_player(tmp_path, volume)
    finally:
        # Clean up temp file
        if tmp_path.exists():
            tmp_path.unlink()
