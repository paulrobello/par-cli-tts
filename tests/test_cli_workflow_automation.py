"""CLI tests for workflow automation features."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from par_tts.cli import tts_cli
from par_tts.providers.base import Voice


@pytest.fixture(autouse=True)
def isolate_config(monkeypatch, tmp_path):
    """Keep CLI tests independent from the developer's real config file."""
    monkeypatch.setattr("par_tts.cli.config_file.platformdirs.user_config_dir", lambda _: str(tmp_path))


class FakeProvider:
    """Provider test double for workflow CLI tests."""

    def __init__(self) -> None:
        self.generated: list[tuple[str, str, dict[str, Any]]] = []
        self.saved_paths: list[Path] = []

    @property
    def name(self) -> str:
        return "Fake TTS"

    @property
    def supported_formats(self) -> list[str]:
        return ["mp3"]

    @property
    def default_model(self) -> str:
        return "fake-model"

    @property
    def default_voice(self) -> str:
        return "nova"

    def generate_speech(self, text: str, voice: str, model: str | None = None, **kwargs: Any) -> bytes | Iterator[bytes]:
        self.generated.append((text, voice, {"model": model, **kwargs}))
        return f"audio:{text}".encode()

    def list_voices(self) -> list[Voice]:
        return [Voice(id="nova", name="Nova")]

    def resolve_voice(self, voice_identifier: str) -> str:
        return voice_identifier.lower()

    def save_audio(self, audio_data: bytes | Iterator[bytes], file_path: str | Path) -> None:
        path = Path(file_path)
        path.write_bytes(audio_data if isinstance(audio_data, bytes) else b"".join(audio_data))
        self.saved_paths.append(path)

    def play_audio(self, audio_data: bytes | Iterator[bytes], volume: float = 1.0) -> None:
        return None


def test_cli_applies_template_variables(monkeypatch):
    """--var should render variables in @template input before synthesis."""
    runner = CliRunner()
    fake_provider = FakeProvider()
    monkeypatch.setattr(tts_cli, "create_provider", lambda *args, **kwargs: fake_provider)

    with runner.isolated_filesystem():
        Path("template.txt").write_text("Hello {{ name }} on {date}", encoding="utf-8")
        result = runner.invoke(
            tts_cli.app,
            ["@template.txt", "--provider", "openai", "--var", "name=Paul", "--var", "date=2026-04-26", "--no-play"],
        )

    assert result.exit_code == 0
    assert fake_provider.generated[0][0] == "Hello Paul on 2026-04-26"


def test_cli_batch_generates_one_file_per_record(monkeypatch, tmp_path):
    """--batch should synthesize each CSV row to its requested output file."""
    runner = CliRunner()
    fake_provider = FakeProvider()
    monkeypatch.setattr(tts_cli, "create_provider", lambda *args, **kwargs: fake_provider)
    batch = tmp_path / "batch.csv"
    out_dir = tmp_path / "out"
    batch.write_text("text,voice,output\nFirst,nova,first.mp3\nSecond,onyx,second.mp3\n", encoding="utf-8")

    result = runner.invoke(
        tts_cli.app,
        ["--batch", str(batch), "--batch-output-dir", str(out_dir), "--provider", "openai", "--no-play"],
    )

    assert result.exit_code == 0
    assert [item[0] for item in fake_provider.generated] == ["First", "Second"]
    assert [item[1] for item in fake_provider.generated] == ["nova", "onyx"]
    assert (out_dir / "first.mp3").read_bytes() == b"audio:First"
    assert (out_dir / "second.mp3").read_bytes() == b"audio:Second"


def test_cli_writes_timestamp_exports_for_generated_text(monkeypatch, tmp_path):
    """--timestamp-output should write rough timing metadata alongside synthesis."""
    runner = CliRunner()
    fake_provider = FakeProvider()
    monkeypatch.setattr(tts_cli, "create_provider", lambda *args, **kwargs: fake_provider)
    timestamps = tmp_path / "captions.srt"

    result = runner.invoke(
        tts_cli.app,
        ["Hello world. Second line.", "--provider", "openai", "--timestamp-output", str(timestamps), "--timestamp-format", "srt", "--no-play"],
    )

    assert result.exit_code == 0
    content = timestamps.read_text(encoding="utf-8")
    assert "00:00:00,000 -->" in content
    assert "Hello world." in content
    assert "Second line." in content


def test_cli_watch_once_regenerates_changed_file(monkeypatch, tmp_path):
    """--watch with --watch-once should synthesize current watched files once for automation/tests."""
    runner = CliRunner()
    fake_provider = FakeProvider()
    monkeypatch.setattr(tts_cli, "create_provider", lambda *args, **kwargs: fake_provider)
    doc = tmp_path / "doc.md"
    out_dir = tmp_path / "audio"
    doc.write_text("Watch me", encoding="utf-8")

    result = runner.invoke(
        tts_cli.app,
        ["--watch", str(doc), "--watch-once", "--batch-output-dir", str(out_dir), "--provider", "openai", "--no-play"],
    )

    assert result.exit_code == 0
    assert fake_provider.generated[0][0] == "Watch me"
    assert (out_dir / "doc.mp3").exists()


def test_cli_notification_mode_applies_low_latency_defaults(monkeypatch):
    """--notification should choose low-latency options for supported providers."""
    runner = CliRunner()
    fake_provider = FakeProvider()
    monkeypatch.setattr(tts_cli, "create_provider", lambda *args, **kwargs: fake_provider)
    monkeypatch.setattr(tts_cli, "postprocess_audio_file", lambda *args, **kwargs: None)

    result = runner.invoke(tts_cli.app, ["ping", "--provider", "openai", "--notification", "--no-play"])

    assert result.exit_code == 0
    generated = fake_provider.generated[0]
    assert generated[2]["model"] == "tts-1"
    assert generated[2]["speed"] == 1.15
