"""Reliability and observability feature tests."""

import json
import logging
from typing import Any

import pytest
from typer.testing import CliRunner

from par_tts.cli import tts_cli
from par_tts.cli.config_file import ConfigFile


@pytest.fixture(autouse=True)
def isolate_config(monkeypatch, tmp_path):
    """Keep CLI tests independent from the developer's real config file."""
    monkeypatch.setattr("par_tts.cli.config_file.platformdirs.user_config_dir", lambda _: str(tmp_path))
    monkeypatch.setattr("par_tts.model_downloader.user_data_dir", lambda *_args, **_kwargs: str(tmp_path / "kokoro"))
    monkeypatch.setattr("par_tts.voice_cache.platformdirs.user_cache_dir", lambda _app: str(tmp_path / "cache"))


def test_config_accepts_observability_settings() -> None:
    """Config files should expose structured logging and retry controls."""
    config = ConfigFile(
        structured_logs=True,
        log_level="DEBUG",
        retry_attempts=2,
        retry_backoff=0.25,
        profiles={"ci": {"structured_logs": True, "retry_attempts": 1, "retry_backoff": 0.0}},
    )

    assert config.structured_logs is True
    assert config.log_level == "DEBUG"
    assert config.retry_attempts == 2
    assert config.retry_backoff == 0.25
    assert config.profiles is not None
    assert config.profiles["ci"].retry_attempts == 1


@pytest.mark.parametrize("bad_level", ["verbose", "TRACE"])
def test_config_rejects_unknown_log_level(bad_level: str) -> None:
    """Log level typos should fail during config validation."""
    with pytest.raises(ValueError):
        ConfigFile(log_level=bad_level)


def test_json_logging_formatter_emits_structured_records() -> None:
    """Structured logging mode should emit machine-parseable JSON records."""
    from par_tts.logging_config import JsonLogFormatter

    record = logging.LogRecord(
        name="par_tts.test",
        level=logging.WARNING,
        pathname=__file__,
        lineno=42,
        msg="retrying %s",
        args=("openai",),
        exc_info=None,
    )

    payload = json.loads(JsonLogFormatter().format(record))

    assert payload["level"] == "WARNING"
    assert payload["logger"] == "par_tts.test"
    assert payload["message"] == "retrying openai"
    assert "timestamp" in payload


def test_retry_policy_retries_then_returns(monkeypatch) -> None:
    """Retry helper should retry transient failures and apply exponential backoff."""
    from par_tts.retry import RetryPolicy, run_with_retries

    attempts = 0
    sleeps: list[float] = []

    def flaky() -> str:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise RuntimeError("temporary failure")
        return "ok"

    monkeypatch.setattr("par_tts.retry.time.sleep", sleeps.append)

    result = run_with_retries(flaky, RetryPolicy(retry_attempts=2, backoff_seconds=0.5), operation="test-op")

    assert result == "ok"
    assert attempts == 3
    assert sleeps == [0.5, 1.0]


def test_create_provider_passes_retry_controls(monkeypatch) -> None:
    """Provider constructors should receive retry/backoff settings from the CLI layer."""
    from par_tts.providers.base import ProviderCapabilities, ProviderPlugin

    captured: dict[str, Any] = {}

    class RetryAwareProvider:
        def __init__(self, **kwargs: Any) -> None:
            captured.update(kwargs)

    plugin = ProviderPlugin(
        name="retry-aware",
        provider_class=RetryAwareProvider,  # type: ignore[arg-type]
        description="Retry-aware fake provider",
        capabilities=ProviderCapabilities(formats=["mp3"]),
        default_model="fake-model",
        default_voice="fake-voice",
        requires_api_key=False,
        source="test",
    )
    monkeypatch.setattr(tts_cli, "get_provider_plugin", lambda name: plugin)
    monkeypatch.setattr(tts_cli, "get_provider_plugins", lambda: {"retry-aware": plugin})

    tts_cli.create_provider("retry-aware", retry_attempts=3, retry_backoff=0.2)

    assert captured["retry_attempts"] == 3
    assert captured["retry_backoff"] == 0.2


def test_doctor_command_prints_offline_diagnostics(monkeypatch) -> None:
    """`par-tts doctor` should run offline diagnostics without creating a provider."""
    runner = CliRunner()

    def fail_create_provider(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("doctor should not create providers or call APIs")

    monkeypatch.setattr(tts_cli, "create_provider", fail_create_provider)
    monkeypatch.setattr("par_tts.diagnostics.sys.platform", "linux")
    monkeypatch.setattr("par_tts.diagnostics.shutil.which", lambda exe: f"/usr/bin/{exe}" if exe == "ffplay" else None)

    result = runner.invoke(tts_cli.app, ["doctor"])

    assert result.exit_code == 0
    assert "PAR TTS Doctor" in result.output
    assert "Audio backends" in result.output
    assert "ffplay" in result.output
    assert "Kokoro models" in result.output
    assert "Environment" in result.output
    assert "ELEVENLABS_API_KEY" in result.output
