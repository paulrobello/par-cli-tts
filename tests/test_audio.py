"""Tests for audio playback utilities."""

from pathlib import Path
from typing import Any

import pytest

from par_tts import audio
from par_tts.errors import TTSError


def test_macos_missing_afplay_fails_with_install_message(monkeypatch, tmp_path):
    """macOS playback should clearly say afplay is required when unavailable."""
    audio_file = tmp_path / "test.mp3"
    audio_file.write_bytes(b"fake")
    monkeypatch.setattr(audio.sys, "platform", "darwin")
    monkeypatch.setattr(audio.shutil, "which", lambda _: None)

    with pytest.raises(TTSError, match="afplay.*install"):
        audio.play_audio_with_player(audio_file)


def test_linux_missing_audio_players_fails_with_install_message(monkeypatch, tmp_path):
    """Linux playback should list supported players when none are installed."""
    audio_file = tmp_path / "test.mp3"
    audio_file.write_bytes(b"fake")
    monkeypatch.setattr(audio.sys, "platform", "linux")
    monkeypatch.setattr(audio.shutil, "which", lambda _: None)

    with pytest.raises(TTSError, match="Install.*aplay.*paplay.*ffplay.*mpg123"):
        audio.play_audio_with_player(audio_file)


def test_windows_missing_powershell_fails_with_install_message(monkeypatch, tmp_path):
    """Windows fallback should clearly say PowerShell or another player is required."""
    audio_file = tmp_path / "test.mp3"
    audio_file.write_bytes(b"fake")
    monkeypatch.setattr(audio.sys, "platform", "win32")
    monkeypatch.setattr(audio.shutil, "which", lambda _: None)

    def fake_run(*args: Any, **kwargs: Any) -> None:
        raise FileNotFoundError("powershell")

    monkeypatch.setattr(audio.subprocess, "run", fake_run)

    with pytest.raises(TTSError, match="PowerShell.*ffplay.*VLC.*mpg123"):
        audio.play_audio_with_player(audio_file)


def test_play_audio_bytes_preserves_missing_player_message(monkeypatch):
    """Byte playback should not hide the underlying missing-player guidance."""
    monkeypatch.setattr(audio.sys, "platform", "linux")
    monkeypatch.setattr(audio.shutil, "which", lambda _: None)

    with pytest.raises(TTSError, match="No audio player found"):
        audio.play_audio_bytes(b"fake", suffix=".mp3")
