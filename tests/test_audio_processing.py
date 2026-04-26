"""Tests for CLI audio post-processing helpers."""

from pathlib import Path
from typing import Any

import pytest

from par_tts.audio_processing import AudioProcessingOptions, build_ffmpeg_postprocess_command, postprocess_audio_file
from par_tts.errors import TTSError


def test_build_ffmpeg_postprocess_command_includes_trim_normalize_and_fades(tmp_path):
    """Post-processing command should include requested filters in a safe argv list."""
    source = tmp_path / "in.wav"
    target = tmp_path / "out.wav"

    command = build_ffmpeg_postprocess_command(
        source,
        target,
        AudioProcessingOptions(trim_silence=True, normalize=True, fade_in_ms=100, fade_out_ms=250),
    )

    assert command[:4] == ["ffmpeg", "-y", "-i", str(source)]
    joined = " ".join(command)
    assert "silenceremove" in joined
    assert "loudnorm" in joined
    assert "afade=t=in" in joined
    assert "afade=t=out" in joined
    assert command[-1] == str(target)


def test_postprocess_audio_file_requires_ffmpeg_when_options_enabled(monkeypatch, tmp_path):
    """Missing ffmpeg should fail clearly instead of pretending processing happened."""
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"fake")
    monkeypatch.setattr("par_tts.audio_processing.shutil.which", lambda _: None)

    with pytest.raises(TTSError, match="ffmpeg"):
        postprocess_audio_file(audio, AudioProcessingOptions(normalize=True))


def test_postprocess_audio_file_replaces_input_with_processed_output(monkeypatch, tmp_path):
    """Successful ffmpeg processing should replace the original file."""
    audio = tmp_path / "audio.wav"
    audio.write_bytes(b"before")
    monkeypatch.setattr("par_tts.audio_processing.shutil.which", lambda _: "/usr/bin/ffmpeg")

    def fake_run(command: list[str], **kwargs: Any) -> None:
        Path(command[-1]).write_bytes(b"after")

    monkeypatch.setattr("par_tts.audio_processing.subprocess.run", fake_run)

    postprocess_audio_file(audio, AudioProcessingOptions(preset="notification"))

    assert audio.read_bytes() == b"after"
