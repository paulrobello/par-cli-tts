"""Audio playback utilities."""

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from par_tts.errors import ErrorType, TTSError


def play_audio_with_player(file_path: Path, volume: float = 1.0) -> None:
    """Play audio using system player with volume support.

    This function detects the operating system and uses the appropriate
    audio player with volume control support.

    Args:
        file_path: Path to the audio file to play.
        volume: Volume level (0.0 = silent, 1.0 = normal, 2.0 = double).

    Raises:
        TTSError: If no suitable audio player is installed or playback fails.
    """
    if sys.platform == "darwin":  # macOS
        # afplay supports volume flag (-v)
        if shutil.which("afplay") is None:
            raise TTSError(
                "Audio playback requires afplay; install or restore macOS command line audio tools.",
                ErrorType.PROVIDER_ERROR,
            )
        try:
            subprocess.run(["afplay", "-v", str(volume), str(file_path)], check=True)
        except subprocess.CalledProcessError as e:
            raise TTSError(f"afplay audio playback failed: {e}", ErrorType.PROVIDER_ERROR) from e
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
        available_players = [(player, args) for player, args in players_with_volume if shutil.which(player)]
        if not available_players:
            raise TTSError(
                "No audio player found. Install aplay, paplay, ffplay, or mpg123 to enable playback.",
                ErrorType.PROVIDER_ERROR,
            )

        failures: list[str] = []
        for player, volume_args in available_players:
            try:
                cmd = [player] + volume_args + [str(file_path)]
                subprocess.run(cmd, check=True)
                return
            except subprocess.CalledProcessError as e:
                failures.append(f"{player}: exit {e.returncode}")
            except FileNotFoundError:
                failures.append(f"{player}: not found")

        raise TTSError(
            f"Audio playback failed with installed players ({'; '.join(failures)}). "
            "Install or configure a working player: aplay, paplay, ffplay, or mpg123.",
            ErrorType.PROVIDER_ERROR,
        )


def _find_windows_audio_player() -> tuple[str, str] | None:
    """Find an available audio player on Windows.

    Checks for ffplay, VLC, and mpg123 in that order.

    Returns:
        Tuple of player name and executable path, or None if no player is available.
    """
    # Prefer ffplay (comes with ffmpeg, most reliable)
    if ffplay := shutil.which("ffplay"):
        return ("ffplay", ffplay)

    # VLC media player — check PATH first, then common install locations.
    if vlc := shutil.which("vlc"):
        return ("vlc", vlc)

    vlc_paths = [
        r"C:\Program Files\VideoLAN\VLC\vlc.exe",
        r"C:\Program Files (x86)\VideoLAN\VLC\vlc.exe",
    ]
    for vlc_path in vlc_paths:
        if Path(vlc_path).exists():
            return ("vlc", vlc_path)

    # mpg123 for Windows
    if mpg123 := shutil.which("mpg123"):
        return ("mpg123", mpg123)

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
        TTSError: If PowerShell is unavailable or playback fails.
    """
    powershell = shutil.which("powershell") or shutil.which("pwsh")
    if powershell is None:
        raise TTSError(
            "Audio playback requires PowerShell, ffplay, VLC, or mpg123 on Windows. "
            "Install ffmpeg (for ffplay), VLC, mpg123, or ensure PowerShell is available.",
            ErrorType.PROVIDER_ERROR,
        )

    # MediaPlayer volume is 0.0 to 1.0, cap values above 1.0
    media_volume = min(volume, 1.0)

    # Pass the file path as a subprocess parameter to avoid command injection.
    # The path is passed as a -Command argument where PowerShell treats it as a
    # literal string via $args[0], never interpolating it into script text.
    ps_script = (
        "$file = $args[0]; "
        "$volume = $args[1]; "
        "$timeout = [int]$args[2]; "
        "$player = New-Object -ComObject MediaPlayer.MediaPlayer; "
        "$player.Open($file); "
        "$player.Volume = $volume; "
        "while ($player.ReadyState -lt 3) { Start-Sleep -Milliseconds 100 }; "
        "$duration = $player.Duration; "
        "if ($duration -gt 0) { $player.Play(); Start-Sleep -Seconds $duration } "
        "else { $player.Play(); Start-Sleep -Seconds $timeout }; "
        "$player.Close(); "
        "[System.Runtime.InteropServices.Marshal]::ReleaseComObject($player) | Out-Null"
    )

    try:
        subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-NonInteractive",
                "-Command",
                ps_script,
                str(file_path),
                str(media_volume),
                str(timeout),
            ],
            check=True,
            timeout=timeout + 10,  # Extra buffer for startup/shutdown
        )
    except subprocess.TimeoutExpired as e:
        raise TTSError(f"Audio playback timed out after {timeout} seconds", ErrorType.PROVIDER_ERROR) from e
    except FileNotFoundError as e:
        raise TTSError(
            "Audio playback requires PowerShell, ffplay, VLC, or mpg123 on Windows. "
            "Install ffmpeg (for ffplay), VLC, mpg123, or ensure PowerShell is available.",
            ErrorType.PROVIDER_ERROR,
        ) from e
    except subprocess.CalledProcessError as e:
        raise TTSError(f"PowerShell audio playback failed: {e}", ErrorType.PROVIDER_ERROR) from e


def _play_audio_windows(file_path: Path, volume: float = 1.0) -> None:
    """Play audio on Windows with volume control.

    Tries external players first (ffplay, VLC, mpg123), then falls back
    to PowerShell MediaPlayer COM object.

    Args:
        file_path: Path to the audio file to play.
        volume: Volume level (0.0 = silent, 1.0 = normal, 2.0 = double).

    Raises:
        TTSError: If no audio playback method succeeds.
    """
    player_info = _find_windows_audio_player()
    player, executable = player_info if player_info else (None, None)

    try:
        if player == "ffplay" and executable:
            # ffplay uses 0-100 volume scale
            subprocess.run(
                [
                    executable,
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
        elif player == "vlc" and executable:
            # VLC volume scale: 0-256 where 256 is 100%
            # Higher values possible but 512 is 200%
            subprocess.run(
                [
                    executable,
                    "--intf",
                    "dummy",
                    "--play-and-exit",
                    "--volume",
                    str(int(volume * 256)),
                    str(file_path),
                ],
                check=True,
            )
        elif player == "mpg123" and executable:
            # mpg123 uses scale factor (32768 = normal)
            subprocess.run(
                [executable, "-f", str(int(volume * 32768)), str(file_path)],
                check=True,
            )
        else:
            # Fallback to PowerShell MediaPlayer
            _play_with_powershell(file_path, volume)
    except TTSError:
        raise
    except FileNotFoundError as e:
        raise TTSError(
            "Audio playback requires ffplay, VLC, mpg123, or PowerShell on Windows. "
            "Install ffmpeg (for ffplay), VLC, mpg123, or ensure PowerShell is available.",
            ErrorType.PROVIDER_ERROR,
        ) from e
    except subprocess.CalledProcessError as e:
        raise TTSError(f"Windows audio playback failed: {e}", ErrorType.PROVIDER_ERROR) from e


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
