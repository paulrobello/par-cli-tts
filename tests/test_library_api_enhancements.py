"""Tests for async APIs, callbacks, option schemas, and reusable pipelines."""

from __future__ import annotations

import asyncio
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

from par_tts import (
    OpenAIOptions,
    SpeechCallbacks,
    SpeechPipeline,
    Voice,
    get_provider_option_schema,
    options_to_kwargs,
)
from par_tts.providers.base import TTSProvider


class FakeProvider(TTSProvider):
    """Small provider implementation for library API tests."""

    PROVIDER_KWARGS = {"speed": 1.0, "stream": False}

    def __init__(self) -> None:
        super().__init__()
        self.generate_calls: list[dict[str, Any]] = []
        self.list_calls = 0

    @property
    def name(self) -> str:
        return "fake"

    @property
    def supported_formats(self) -> list[str]:
        return ["wav"]

    @property
    def default_model(self) -> str:
        return "fake-model"

    @property
    def default_voice(self) -> str:
        return "fake-voice"

    def generate_speech(
        self,
        text: str,
        voice: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> bytes | Iterator[bytes]:
        self.generate_calls.append({"text": text, "voice": voice, "model": model, "kwargs": kwargs})
        if kwargs.get("stream"):
            return iter([b"chunk-1", b"chunk-2"])
        return b"audio-bytes"

    def list_voices(self) -> list[Voice]:
        self.list_calls += 1
        return [Voice(id="resolved-voice", name="Resolved Voice")]

    def resolve_voice(self, voice_identifier: str) -> str:
        return f"resolved-{voice_identifier}"


class FailingProvider(FakeProvider):
    def generate_speech(
        self,
        text: str,
        voice: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> bytes | Iterator[bytes]:
        raise RuntimeError("generation failed")


def test_provider_option_schema_lookup_and_validation() -> None:
    """Provider option schemas should be discoverable and validate bad values."""
    assert get_provider_option_schema("openai") is OpenAIOptions

    with pytest.raises(ValueError, match="speed"):
        OpenAIOptions(speed=5.0)

    kwargs = options_to_kwargs(OpenAIOptions(speed=1.25, response_format="wav"))

    assert kwargs == {"speed": 1.25, "response_format": "wav"}


def test_speech_pipeline_reuses_provider_options_and_saves_audio(tmp_path: Path) -> None:
    """SpeechPipeline should keep provider/voice/options for repeated synthesis."""
    provider = FakeProvider()
    completed = []
    callbacks = SpeechCallbacks(on_complete=completed.append)
    pipeline = SpeechPipeline(
        provider=provider,
        voice="voice",
        model="pipeline-model",
        options={"speed": 1.5},
        callbacks=callbacks,
    )

    output_path = pipeline.synthesize_to_file("hello", tmp_path / "hello.wav")

    assert output_path.read_bytes() == b"audio-bytes"
    assert provider.generate_calls == [
        {
            "text": "hello",
            "voice": "resolved-voice",
            "model": "pipeline-model",
            "kwargs": {"speed": 1.5},
        }
    ]
    assert completed[0].provider == "fake"
    assert completed[0].bytes_generated == len(b"audio-bytes")


def test_speech_pipeline_calls_error_callback() -> None:
    """Pipeline errors should be observable through on_error before reraising."""
    errors = []
    pipeline = SpeechPipeline(
        provider=FailingProvider(), voice="voice", callbacks=SpeechCallbacks(on_error=errors.append)
    )

    with pytest.raises(RuntimeError, match="generation failed"):
        pipeline.synthesize("hello")

    assert len(errors) == 1
    assert str(errors[0]) == "generation failed"


def test_async_provider_methods_list_and_stream_with_callbacks() -> None:
    """Async provider APIs should support list_voices and streamed chunks."""

    async def run() -> None:
        provider = FakeProvider()
        chunks_seen: list[bytes] = []
        progress_seen = []
        completed = []
        callbacks = SpeechCallbacks(
            on_chunk=chunks_seen.append,
            on_progress=progress_seen.append,
            on_complete=completed.append,
        )

        voices = await provider.list_voices_async()
        audio = await provider.generate_speech_async("hello", "voice", stream=True, callbacks=callbacks)
        chunks = [chunk async for chunk in audio]

        assert voices == [Voice(id="resolved-voice", name="Resolved Voice")]
        assert chunks == [b"chunk-1", b"chunk-2"]
        assert chunks_seen == chunks
        assert [progress.bytes_generated for progress in progress_seen] == [7, 14]
        assert completed[0].chunks_generated == 2
        assert completed[0].bytes_generated == 14

    asyncio.run(run())


def test_async_pipeline_synthesizes_to_file(tmp_path: Path) -> None:
    """SpeechPipeline async helpers should mirror the sync file workflow."""

    async def run() -> None:
        pipeline = SpeechPipeline(provider=FakeProvider(), voice="voice")

        output_path = await pipeline.synthesize_to_file_async("hello", tmp_path / "async.wav")

        assert output_path.read_bytes() == b"audio-bytes"

    asyncio.run(run())
