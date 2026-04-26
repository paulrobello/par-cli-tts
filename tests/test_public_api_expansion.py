"""Tests for the expanded stable public API surface."""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from par_tts.providers.base import ProviderCapabilities, ProviderPlugin, TTSProvider, Voice


class PublicFakeProvider(TTSProvider):
    """Provider test double used by public API tests."""

    def __init__(self, api_key: str | None = None, **kwargs: Any) -> None:
        super().__init__(api_key=api_key, **kwargs)
        self.generated: list[dict[str, Any]] = []

    @property
    def name(self) -> str:
        return "Public Fake"

    @property
    def supported_formats(self) -> list[str]:
        return ["wav"]

    @property
    def default_model(self) -> str:
        return "fake-model"

    @property
    def default_voice(self) -> str:
        return "voice"

    def generate_speech(
        self,
        text: str,
        voice: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> bytes | Iterator[bytes]:
        self.generated.append({"text": text, "voice": voice, "model": model, "kwargs": kwargs})
        return b"audio"

    def list_voices(self) -> list[Voice]:
        return [
            Voice(id="nova", name="Nova", labels=["warm", "friendly"], category="OpenAI TTS"),
            Voice(id="onyx", name="Onyx", labels=["deep"], category="OpenAI TTS"),
        ]

    def resolve_voice(self, voice_identifier: str) -> str:
        return voice_identifier


def test_create_provider_public_factory_uses_plugin_env_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    """create_provider should instantiate providers without importing CLI code."""
    import par_tts

    plugin = ProviderPlugin(
        name="fake-cloud",
        provider_class=PublicFakeProvider,
        description="Fake cloud",
        capabilities=ProviderCapabilities(formats=["wav"]),
        default_model="fake-model",
        default_voice="voice",
        requires_api_key=True,
        api_key_env_vars=("FAKE_TTS_API_KEY",),
    )
    monkeypatch.setattr("par_tts.provider_factory.get_provider_plugin", lambda name: plugin)
    monkeypatch.setenv("FAKE_TTS_API_KEY", "secret")

    provider = par_tts.create_provider("fake-cloud", provider_kwargs={"retry_attempts": 1})

    assert isinstance(provider, PublicFakeProvider)
    assert provider.api_key == "secret"
    assert provider.retry_policy.retry_attempts == 1


def test_create_provider_public_factory_raises_tts_error_for_missing_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Missing API keys should fail with public TTSError/ErrorType values."""
    import par_tts

    plugin = ProviderPlugin(
        name="fake-cloud",
        provider_class=PublicFakeProvider,
        description="Fake cloud",
        capabilities=ProviderCapabilities(formats=["wav"]),
        default_model="fake-model",
        default_voice="voice",
        requires_api_key=True,
        api_key_env_vars=("FAKE_TTS_API_KEY",),
    )
    monkeypatch.setattr("par_tts.provider_factory.get_provider_plugin", lambda name: plugin)
    monkeypatch.delenv("FAKE_TTS_API_KEY", raising=False)

    with pytest.raises(par_tts.TTSError) as exc_info:
        par_tts.create_provider("fake-cloud")

    assert exc_info.value.error_type is par_tts.ErrorType.MISSING_API_KEY


def test_public_text_processing_options_build_segments() -> None:
    """TextProcessingOptions should provide a stable typed input for segmentation."""
    from par_tts import TextProcessingOptions, build_text_segments

    options = TextProcessingOptions(chunk=True, max_chars=12, pronunciations={"NASA": "N A S A"}, auto_lang=True)

    segments = build_text_segments("NASA launches. Second sentence.", options=options)

    assert [segment.text for segment in segments] == ["N A S A", "launches.", "Second", "sentence."]
    assert {segment.lang for segment in segments} == {"en-us"}


def test_speech_pipeline_applies_text_and_audio_processing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """SpeechPipeline should expose text and audio processing through the facade."""
    from par_tts import AudioProcessingOptions, SpeechPipeline, TextProcessingOptions

    processed_paths: list[tuple[Path, AudioProcessingOptions]] = []

    def fake_postprocess(path: Path, options: AudioProcessingOptions) -> None:
        processed_paths.append((path, options))
        path.write_bytes(path.read_bytes() + b" processed")

    monkeypatch.setattr("par_tts.pipeline.postprocess_audio_file", fake_postprocess)
    provider = PublicFakeProvider()
    pipeline = SpeechPipeline(
        provider=provider,
        voice="nova",
        text_processing=TextProcessingOptions(pronunciations={"NASA": "N A S A"}),
        audio_processing=AudioProcessingOptions(normalize=True),
    )

    output_path = pipeline.synthesize_to_file("NASA", tmp_path / "out.wav")

    assert output_path.read_bytes() == b"audio processed"
    assert provider.generated[0]["text"] == "N A S A"
    assert processed_paths == [(output_path, AudioProcessingOptions(normalize=True))]


def test_public_search_voices_finds_by_label() -> None:
    """Voice search should be available outside the CLI module."""
    from par_tts import search_voices

    matches = search_voices(PublicFakeProvider().list_voices(), "warm")

    assert [voice.id for voice in matches] == ["nova"]


def test_public_voice_packs_and_cost_estimation() -> None:
    """Voice-pack metadata and static cost estimates should be public."""
    from par_tts import CostEstimate, VoicePack, estimate_synthesis_cost, get_voice_pack, load_voice_packs

    packs = load_voice_packs()
    pack = get_voice_pack("assistant")
    estimate = estimate_synthesis_cost("openai", "tts-1", "hello")

    assert "assistant" in packs
    assert isinstance(pack, VoicePack)
    assert isinstance(estimate, CostEstimate)
    assert estimate.characters == 5
    assert estimate.cost_usd is not None


def test_public_diagnostics_and_model_manager_exports() -> None:
    """Diagnostics and Kokoro model manager should be documented public imports."""
    from par_tts import DiagnosticCheck, ModelDownloader, collect_diagnostics

    assert DiagnosticCheck(name="x", ok=True, detail="ok").ok is True
    assert callable(collect_diagnostics)
    assert ModelDownloader is not None
