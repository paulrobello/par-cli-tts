"""CLI quick-win feature tests."""

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from par_tts.audio_processing import AudioProcessingOptions
from par_tts.cli import tts_cli
from par_tts.cli.completions import generate_completion_script
from par_tts.errors import TTSError
from par_tts.providers.base import Voice
from par_tts.text_processing import TextSegment


@pytest.fixture(autouse=True)
def isolate_config(monkeypatch, tmp_path):
    """Keep CLI tests independent from the developer's real config file."""
    monkeypatch.setattr("par_tts.cli.config_file.platformdirs.user_config_dir", lambda _: str(tmp_path))


class FakeProvider:
    """Small provider test double for CLI tests."""

    PROVIDER_KWARGS = {"speed": 1.0, "response_format": "mp3", "instructions": None}

    def __init__(self) -> None:
        self.generated_texts: list[str] = []
        self.generated_kwargs: list[dict[str, Any]] = []
        self.resolved_voices: list[str] = []
        self.play_count = 0

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
        self.generated_texts.append(text)
        self.generated_kwargs.append(kwargs)
        return b"fake audio"

    def list_voices(self) -> list[Voice]:
        return [
            Voice(id="nova", name="Nova", labels=["warm", "friendly"], category="OpenAI TTS"),
            Voice(id="onyx", name="Onyx", labels=["deep", "authoritative"], category="OpenAI TTS"),
        ]

    def resolve_voice(self, voice_identifier: str) -> str:
        self.resolved_voices.append(voice_identifier)
        return voice_identifier.lower()

    def save_audio(self, audio_data: bytes | Iterator[bytes], file_path: str | Path) -> None:
        Path(file_path).write_bytes(b"fake audio")

    def play_audio(self, audio_data: bytes | Iterator[bytes], volume: float = 1.0) -> None:
        self.play_count += 1


def test_capabilities_prints_matrix_without_creating_provider(monkeypatch):
    """--capabilities should inspect plugin metadata without provider side effects."""
    runner = CliRunner()

    def fail_create_provider(*args: Any, **kwargs: Any) -> FakeProvider:
        raise AssertionError("capabilities should not create a provider")

    monkeypatch.setattr(tts_cli, "create_provider", fail_create_provider)

    result = runner.invoke(tts_cli.app, ["--capabilities"])

    assert result.exit_code == 0
    assert "Provider Capabilities" in result.output
    assert "kokoro-onnx" in result.output
    assert "openai" in result.output
    assert "Speed" in result.output
    assert "Streaming" in result.output


def test_dry_run_prints_plan_without_creating_provider(monkeypatch):
    """--dry-run should show the planned operation without provider side effects."""
    runner = CliRunner()

    def fail_create_provider(*args: Any, **kwargs: Any) -> FakeProvider:
        raise AssertionError("dry-run should not create a provider")

    monkeypatch.setattr(tts_cli, "create_provider", fail_create_provider)

    result = runner.invoke(
        tts_cli.app,
        ["hello", "--provider", "openai", "--voice", "nova", "--dry-run"],
    )

    assert result.exit_code == 0
    assert "Dry run" in result.output
    assert "provider" in result.output
    assert "openai" in result.output
    assert "text_length" in result.output
    assert "5" in result.output


def test_estimate_cost_prints_estimate_without_creating_provider(monkeypatch):
    """--estimate-cost should be a static estimate and not initialize providers."""
    runner = CliRunner()

    def fail_create_provider(*args: Any, **kwargs: Any) -> FakeProvider:
        raise AssertionError("estimate-cost should not create a provider")

    monkeypatch.setattr(tts_cli, "create_provider", fail_create_provider)

    result = runner.invoke(
        tts_cli.app,
        ["hello world", "--provider", "openai", "--model", "tts-1", "--estimate-cost"],
    )

    assert result.exit_code == 0
    assert "Cost estimate" in result.output
    assert "openai" in result.output
    assert "11" in result.output
    assert "$" in result.output


def test_search_voices_filters_fake_provider(monkeypatch):
    """--search-voices should search voice name, id, labels, and category."""
    runner = CliRunner()
    fake_provider = FakeProvider()
    monkeypatch.setattr(tts_cli, "create_provider", lambda *args, **kwargs: fake_provider)

    result = runner.invoke(tts_cli.app, ["--provider", "openai", "--search-voices", "warm"])

    assert result.exit_code == 0
    assert "nova" in result.output
    assert "Nova" in result.output
    assert "onyx" not in result.output


def test_create_provider_uses_external_plugin_without_api_key(monkeypatch):
    """External plugin providers without API keys should instantiate through metadata."""
    from par_tts.providers.base import ProviderCapabilities, ProviderPlugin

    plugin = ProviderPlugin(
        name="external",
        provider_class=FakeProvider,  # type: ignore[arg-type]
        description="External provider",
        capabilities=ProviderCapabilities(formats=["mp3"]),
        default_model="external-model",
        default_voice="external-voice",
        requires_api_key=False,
        source="test",
    )
    monkeypatch.setattr(tts_cli, "get_provider_plugin", lambda name: plugin)
    monkeypatch.setattr(tts_cli, "get_provider_plugins", lambda: {"external": plugin})

    provider = tts_cli.create_provider("external")

    assert isinstance(provider, FakeProvider)


def test_benchmark_uses_plugin_default_voice_for_external_provider(monkeypatch):
    """Benchmark should use plugin default_voice when no CLI voice is supplied."""
    from par_tts.providers.base import ProviderCapabilities, ProviderPlugin

    runner = CliRunner()
    fake_provider = FakeProvider()
    plugin = ProviderPlugin(
        name="external",
        provider_class=FakeProvider,  # type: ignore[arg-type]
        description="External provider",
        capabilities=ProviderCapabilities(formats=["mp3"]),
        default_model="external-model",
        default_voice="external-voice",
        requires_api_key=False,
        source="test",
    )
    monkeypatch.setattr(tts_cli, "get_provider_plugin", lambda name: plugin)
    monkeypatch.setattr(tts_cli, "get_provider_plugins", lambda: {"external": plugin})
    monkeypatch.setattr(tts_cli, "create_provider", lambda *args, **kwargs: fake_provider)

    result = runner.invoke(tts_cli.app, ["hello", "--benchmark", "--benchmark-provider", "external"])

    assert result.exit_code == 0
    assert fake_provider.resolved_voices == ["external-voice"]


def test_run_provider_benchmark_measures_fake_provider():
    """Benchmark helper should generate speech repeatedly and report objective metrics."""
    fake_provider = FakeProvider()

    results = tts_cli.run_provider_benchmark(
        tts_provider=fake_provider,  # type: ignore[arg-type]
        provider="openai",
        text="hello",
        voice="nova",
        model=None,
        repeat_count=2,
        stability=0.5,
        similarity_boost=0.5,
        speed=1.0,
        response_format="mp3",
        lang="en-us",
        instructions=None,
    )

    assert len(results) == 2
    assert fake_provider.generated_texts == ["hello", "hello"]
    assert all(result.provider == "openai" for result in results)
    assert all(result.output_bytes == 10 for result in results)
    assert all(result.cost_usd is not None for result in results)


def test_benchmark_cli_prints_results_without_normal_generation(monkeypatch):
    """--benchmark should print benchmark results for the selected provider."""
    runner = CliRunner()
    fake_provider = FakeProvider()
    monkeypatch.setattr(tts_cli, "create_provider", lambda *args, **kwargs: fake_provider)

    result = runner.invoke(
        tts_cli.app,
        ["hello", "--provider", "openai", "--benchmark", "--benchmark-repeat", "1"],
    )

    assert result.exit_code == 0
    assert "Voice benchmark" in result.output
    assert "openai" in result.output
    assert fake_provider.generated_texts == ["hello"]


def test_from_clipboard_uses_clipboard_text(monkeypatch):
    """--from-clipboard should use clipboard text as synthesis input."""
    runner = CliRunner()
    fake_provider = FakeProvider()
    monkeypatch.setattr(tts_cli, "create_provider", lambda *args, **kwargs: fake_provider)
    monkeypatch.setattr(tts_cli, "read_clipboard_text", lambda: "clip text")

    result = runner.invoke(tts_cli.app, ["--from-clipboard", "--provider", "openai", "--no-play"])

    assert result.exit_code == 0
    assert fake_provider.generated_texts == ["clip text"]
    assert "Summary" in result.output


def test_watch_stdin_processes_each_non_empty_line(monkeypatch):
    """--watch-stdin should synthesize each non-empty stdin line until EOF."""
    runner = CliRunner()
    fake_provider = FakeProvider()
    monkeypatch.setattr(tts_cli, "create_provider", lambda *args, **kwargs: fake_provider)

    result = runner.invoke(
        tts_cli.app,
        ["--watch-stdin", "--provider", "openai", "--no-play"],
        input="one\n\n two \n",
    )

    assert result.exit_code == 0
    assert fake_provider.generated_texts == ["one", "two"]


def test_summary_prints_after_generation(monkeypatch):
    """Normal generation should print a compact post-run summary."""
    runner = CliRunner()
    fake_provider = FakeProvider()
    monkeypatch.setattr(tts_cli, "create_provider", lambda *args, **kwargs: fake_provider)

    result = runner.invoke(tts_cli.app, ["hello", "--provider", "openai", "--voice", "nova", "--no-play"])

    assert result.exit_code == 0
    assert "Summary" in result.output
    assert "openai" in result.output
    assert "5 chars" in result.output


def test_chunking_generates_each_sentence_chunk(monkeypatch):
    """--chunk should split long text and synthesize each chunk separately."""
    runner = CliRunner()
    fake_provider = FakeProvider()
    monkeypatch.setattr(tts_cli, "create_provider", lambda *args, **kwargs: fake_provider)

    result = runner.invoke(
        tts_cli.app,
        ["One sentence. Two sentence.", "--provider", "openai", "--chunk", "--max-chars", "20", "--no-play"],
    )

    assert result.exit_code == 0
    assert fake_provider.generated_texts == ["One sentence.", "Two sentence."]


def test_pronunciation_auto_lang_and_markup_are_applied(monkeypatch):
    """CLI should apply pronunciation rewrites, markup parsing, and auto language hints."""
    runner = CliRunner()
    fake_provider = FakeProvider()
    monkeypatch.setattr(tts_cli, "create_provider", lambda *args, **kwargs: fake_provider)

    result = runner.invoke(
        tts_cli.app,
        [
            "NASA says <prosody rate=\"slow\">hello</prosody>",
            "--provider",
            "openai",
            "--pronunciation",
            "NASA=N A S A",
            "--markup",
            "--auto-lang",
            "--no-play",
        ],
    )

    assert result.exit_code == 0
    assert fake_provider.generated_texts == ["N A S A says hello"]
    assert fake_provider.generated_kwargs[0]["speed"] == 0.85


def test_voice_sections_resolve_and_generate_each_voice(monkeypatch):
    """--voice-sections should resolve voices independently per paragraph."""
    runner = CliRunner()
    fake_provider = FakeProvider()
    monkeypatch.setattr(tts_cli, "create_provider", lambda *args, **kwargs: fake_provider)

    result = runner.invoke(
        tts_cli.app,
        ["voice=nova | Hello\n\nvoice=onyx | World", "--provider", "openai", "--voice-sections", "--no-play"],
    )

    assert result.exit_code == 0
    assert fake_provider.generated_texts == ["Hello", "World"]
    assert fake_provider.resolved_voices[-2:] == ["nova", "onyx"]


def test_post_processing_options_are_passed_to_generation(monkeypatch):
    """Post-processing flags should run after saved audio is written."""
    runner = CliRunner()
    fake_provider = FakeProvider()
    processed: list[tuple[Path, str | None]] = []
    monkeypatch.setattr(tts_cli, "create_provider", lambda *args, **kwargs: fake_provider)

    def fake_postprocess(path: Path, options: Any) -> None:
        processed.append((path, options.preset))

    monkeypatch.setattr(tts_cli, "postprocess_audio_file", fake_postprocess)

    result = runner.invoke(
        tts_cli.app,
        ["hello", "--provider", "openai", "--no-play", "--normalize", "--trim-silence", "--post-process-preset", "podcast"],
    )

    assert result.exit_code == 0
    assert processed
    assert processed[0][1] == "podcast"


def test_missing_ffmpeg_message_is_preserved_for_post_processing(monkeypatch, tmp_path):
    """Missing ffmpeg during post-processing should mention ffmpeg, not a generic generation failure."""
    fake_provider = FakeProvider()
    monkeypatch.setattr("par_tts.audio_processing.shutil.which", lambda _: None)

    with pytest.raises(TTSError, match="ffmpeg"):
        tts_cli.handle_speech_generation(
            text="hello",
            tts_provider=fake_provider,  # type: ignore[arg-type]
            provider="openai",
            voice="nova",
            model=None,
            output=tmp_path / "out.mp3",
            play_audio=False,
            keep_temp=False,
            temp_dir=None,
            volume=1.0,
            debug=False,
            stability=0.5,
            similarity_boost=0.5,
            speed=1.0,
            response_format="mp3",
            lang="en-us",
            instructions=None,
            audio_processing=AudioProcessingOptions(normalize=True),
        )


def test_missing_ffmpeg_message_is_preserved_for_chunk_join(monkeypatch, tmp_path):
    """Missing ffmpeg during chunk joining should mention ffmpeg clearly."""
    fake_provider = FakeProvider()
    monkeypatch.setattr("par_tts.audio_processing.shutil.which", lambda _: None)

    with pytest.raises(TTSError, match="ffmpeg"):
        tts_cli.handle_segmented_speech_generation(
            segments=[TextSegment("one"), TextSegment("two")],
            tts_provider=fake_provider,  # type: ignore[arg-type]
            provider="openai",
            default_voice="nova",
            model=None,
            output=tmp_path / "joined.mp3",
            play_audio=False,
            keep_temp=False,
            temp_dir=None,
            volume=1.0,
            debug=False,
            stability=0.5,
            similarity_boost=0.5,
            speed=1.0,
            response_format="mp3",
            lang="en-us",
            instructions=None,
        )


def test_list_voice_packs_does_not_create_provider(monkeypatch):
    runner = CliRunner()

    def fail_create_provider(*args: Any, **kwargs: Any) -> FakeProvider:
        raise AssertionError("voice-pack listing should not create a provider")

    monkeypatch.setattr(tts_cli, "create_provider", fail_create_provider)

    result = runner.invoke(tts_cli.app, ["--list-voice-packs"])

    assert result.exit_code == 0
    assert "Voice packs" in result.output
    assert "assistant" in result.output
    assert "alerts" in result.output


def test_show_voice_pack_prints_recommendations_without_provider(monkeypatch):
    runner = CliRunner()

    def fail_create_provider(*args: Any, **kwargs: Any) -> FakeProvider:
        raise AssertionError("voice-pack display should not create a provider")

    monkeypatch.setattr(tts_cli, "create_provider", fail_create_provider)

    result = runner.invoke(tts_cli.app, ["--show-voice-pack", "assistant"])

    assert result.exit_code == 0
    assert "assistant" in result.output
    assert "Provider" in result.output
    assert "Voice" in result.output


def test_show_unknown_voice_pack_fails_cleanly():
    runner = CliRunner()

    result = runner.invoke(tts_cli.app, ["--show-voice-pack", "missing-pack"])

    assert result.exit_code != 0
    assert "Unknown voice pack" in result.output
    assert "assistant" in result.output


def test_generate_completion_script_uses_typer_api_without_fallback_delegate():
    script = generate_completion_script("bash")

    assert "_PAR_TTS_COMPLETE" in script
    assert "complete_bash" in script
    assert "Shell source not supported" not in script
    assert 'eval "$(_PAR_TTS_COMPLETE=bash_source par-tts)"' not in script


def test_completion_script_prints_for_supported_shell_without_provider_or_config(monkeypatch):
    runner = CliRunner()

    def fail_create_provider(*args: Any, **kwargs: Any) -> FakeProvider:
        raise AssertionError("completion generation should not create a provider")

    def noisy_load_config(self: Any) -> None:
        print("Loaded config from test marker")
        raise AssertionError("completion generation should not load config")

    monkeypatch.setattr(tts_cli, "create_provider", fail_create_provider)
    monkeypatch.setattr(
        tts_cli,
        "load_dotenv",
        lambda: (_ for _ in ()).throw(AssertionError("completion generation should not load dotenv")),
    )
    monkeypatch.setattr("par_tts.cli.config_file.ConfigManager.load_config", noisy_load_config)

    result = runner.invoke(tts_cli.app, ["--completion", "bash"])

    assert result.exit_code == 0
    assert "_PAR_TTS_COMPLETE" in result.output
    assert "complete_bash" in result.output
    assert "par-tts" in result.output
    assert "Loaded config from" not in result.output
    assert "Shell source not supported" not in result.output


def test_completion_install_prints_shell_specific_instructions_without_config(monkeypatch):
    runner = CliRunner()

    def fail_create_provider(*args: Any, **kwargs: Any) -> FakeProvider:
        raise AssertionError("completion install help should not create a provider")

    def noisy_load_config(self: Any) -> None:
        print("Loaded config from test marker")
        raise AssertionError("completion install help should not load config")

    monkeypatch.setattr(tts_cli, "create_provider", fail_create_provider)
    monkeypatch.setattr(
        tts_cli,
        "load_dotenv",
        lambda: (_ for _ in ()).throw(AssertionError("completion install help should not load dotenv")),
    )
    monkeypatch.setattr("par_tts.cli.config_file.ConfigManager.load_config", noisy_load_config)

    result = runner.invoke(tts_cli.app, ["--completion-install", "fish"])

    assert result.exit_code == 0
    assert "fish" in result.output.lower()
    assert "par-tts --completion fish" in result.output
    assert "Loaded config from" not in result.output
    assert "Shell source not supported" not in result.output


def test_completion_rejects_unknown_shell():
    runner = CliRunner()

    result = runner.invoke(tts_cli.app, ["--completion", "powershell"])

    assert result.exit_code != 0
    assert "Unsupported shell" in result.output
    assert "bash" in result.output
