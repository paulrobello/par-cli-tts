"""Reusable speech pipeline objects for library integrations."""

from __future__ import annotations

import asyncio
import time
from collections.abc import AsyncIterator
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from par_tts.audio_processing import AudioProcessingOptions, concat_audio_files, postprocess_audio_file
from par_tts.providers.base import (
    AsyncAudioData,
    AudioData,
    ProviderOptions,
    SpeechCallbacks,
    TTSProvider,
    Voice,
    apply_speech_callbacks,
    emit_error_callback,
    options_to_kwargs,
)
from par_tts.providers.registry import get_provider_classes
from par_tts.text_processing import TextProcessingOptions, TextSegment, build_text_segments


@dataclass
class SpeechPipeline:
    """Pre-configured reusable speech generation pipeline.

    A pipeline keeps one provider instance plus default voice/model/options so
    long-running applications can issue repeated synthesis requests without
    rebuilding the same configuration each time.
    """

    provider: TTSProvider
    voice: str | None = None
    model: str | None = None
    options: ProviderOptions | dict[str, Any] | None = None
    callbacks: SpeechCallbacks | None = None
    text_processing: TextProcessingOptions | None = None
    audio_processing: AudioProcessingOptions | None = None
    resolve_voices: bool = True
    _resolved_voice_cache: dict[str, str] = field(default_factory=dict, init=False, repr=False)

    @classmethod
    def from_provider_name(
        cls,
        provider_name: str,
        *,
        api_key: str | None = None,
        provider_kwargs: dict[str, Any] | None = None,
        voice: str | None = None,
        model: str | None = None,
        options: ProviderOptions | dict[str, Any] | None = None,
        callbacks: SpeechCallbacks | None = None,
        text_processing: TextProcessingOptions | None = None,
        audio_processing: AudioProcessingOptions | None = None,
        resolve_voices: bool = True,
    ) -> SpeechPipeline:
        """Create a pipeline by provider registry name."""
        providers = get_provider_classes()
        if provider_name not in providers:
            raise ValueError(f"Unknown provider '{provider_name}'. Available: {', '.join(sorted(providers))}")
        provider = providers[provider_name](api_key=api_key, **(provider_kwargs or {}))
        return cls(
            provider=provider,
            voice=voice,
            model=model,
            options=options,
            callbacks=callbacks,
            text_processing=text_processing,
            audio_processing=audio_processing,
            resolve_voices=resolve_voices,
        )

    def list_voices(self) -> list[Voice]:
        """List voices through the configured provider."""
        return self.provider.list_voices()

    async def list_voices_async(self) -> list[Voice]:
        """Async equivalent of ``list_voices()``."""
        return await self.provider.list_voices_async()

    def synthesize(
        self,
        text: str,
        *,
        voice: str | None = None,
        model: str | None = None,
        options: ProviderOptions | dict[str, Any] | None = None,
        callbacks: SpeechCallbacks | None = None,
    ) -> AudioData:
        """Generate speech with the pipeline defaults plus per-call overrides."""
        active_callbacks = callbacks or self.callbacks
        start_time = time.perf_counter()
        try:
            segment = self._single_segment(text)
            audio_data = self.provider.generate_speech(
                text=segment.text,
                voice=self._resolve_voice(voice or segment.voice),
                model=model if model is not None else self.model,
                **self._merged_options(options, segment),
            )
        except Exception as exc:
            emit_error_callback(active_callbacks, exc)
            raise
        return apply_speech_callbacks(
            audio_data,
            active_callbacks,
            provider=self.provider.name,
            text_chars=len(text),
            start_time=start_time,
        )

    def synthesize_to_file(
        self,
        text: str,
        file_path: str | Path,
        *,
        voice: str | None = None,
        model: str | None = None,
        options: ProviderOptions | dict[str, Any] | None = None,
        callbacks: SpeechCallbacks | None = None,
    ) -> Path:
        """Generate speech and save it to ``file_path``."""
        path = Path(file_path)
        segments = self._segments(text)
        if len(segments) == 1:
            segment = segments[0]
            audio_data = self.synthesize(
                segment.text, voice=voice or segment.voice, model=model, options=options, callbacks=callbacks
            )
            self.provider.save_audio(audio_data, path)
            self._postprocess(path)
            return path

        chunk_paths: list[Path] = []
        for index, segment in enumerate(segments, start=1):
            chunk_path = path.with_name(f"{path.stem}.part{index:04d}{path.suffix}")
            audio_data = self.synthesize(
                segment.text, voice=voice or segment.voice, model=model, options=options, callbacks=callbacks
            )
            self.provider.save_audio(audio_data, chunk_path)
            chunk_paths.append(chunk_path)
        concat_audio_files(chunk_paths, path)
        for chunk_path in chunk_paths:
            chunk_path.unlink(missing_ok=True)
        self._postprocess(path)
        return path

    async def synthesize_async(
        self,
        text: str,
        *,
        voice: str | None = None,
        model: str | None = None,
        options: ProviderOptions | dict[str, Any] | None = None,
        callbacks: SpeechCallbacks | None = None,
    ) -> AsyncAudioData:
        """Async equivalent of ``synthesize()``."""
        segment = self._single_segment(text)
        return await self.provider.generate_speech_async(
            text=segment.text,
            voice=self._resolve_voice(voice or segment.voice),
            model=model if model is not None else self.model,
            callbacks=callbacks or self.callbacks,
            **self._merged_options(options, segment),
        )

    async def synthesize_to_file_async(
        self,
        text: str,
        file_path: str | Path,
        *,
        voice: str | None = None,
        model: str | None = None,
        options: ProviderOptions | dict[str, Any] | None = None,
        callbacks: SpeechCallbacks | None = None,
    ) -> Path:
        """Async equivalent of ``synthesize_to_file()``."""
        path = Path(file_path)
        segments = self._segments(text)
        if len(segments) == 1:
            segment = segments[0]
            audio_data = await self.synthesize_async(
                segment.text,
                voice=voice or segment.voice,
                model=model,
                options=options,
                callbacks=callbacks,
            )
            if isinstance(audio_data, bytes):
                await asyncio.to_thread(self.provider.save_audio, audio_data, path)
            else:
                await _save_async_audio_stream(audio_data, path)
            await asyncio.to_thread(self._postprocess, path)
            return path

        chunk_paths: list[Path] = []
        for index, segment in enumerate(segments, start=1):
            chunk_path = path.with_name(f"{path.stem}.part{index:04d}{path.suffix}")
            audio_data = await self.synthesize_async(
                segment.text,
                voice=voice or segment.voice,
                model=model,
                options=options,
                callbacks=callbacks,
            )
            if isinstance(audio_data, bytes):
                await asyncio.to_thread(self.provider.save_audio, audio_data, chunk_path)
            else:
                await _save_async_audio_stream(audio_data, chunk_path)
            chunk_paths.append(chunk_path)
        await asyncio.to_thread(concat_audio_files, chunk_paths, path)
        for chunk_path in chunk_paths:
            chunk_path.unlink(missing_ok=True)
        await asyncio.to_thread(self._postprocess, path)
        return path

    def _resolve_voice(self, voice: str | None) -> str:
        requested_voice = voice or self.voice or self.provider.default_voice
        if not self.resolve_voices:
            return requested_voice
        if requested_voice not in self._resolved_voice_cache:
            self._resolved_voice_cache[requested_voice] = self.provider.resolve_voice(requested_voice)
        return self._resolved_voice_cache[requested_voice]

    def _merged_options(
        self,
        options: ProviderOptions | dict[str, Any] | None,
        segment: TextSegment | None = None,
    ) -> dict[str, Any]:
        merged: dict[str, Any] = {}
        if self.options is not None:
            merged.update(options_to_kwargs(self.options))
        if options is not None:
            merged.update(options_to_kwargs(options))
        if segment and segment.speed is not None:
            merged["speed"] = segment.speed
        if segment and segment.lang is not None:
            merged["lang"] = segment.lang
        return merged

    def _segments(self, text: str) -> list[TextSegment]:
        return (
            build_text_segments(text, options=self.text_processing)
            if self.text_processing
            else [TextSegment(text=text)]
        )

    def _single_segment(self, text: str) -> TextSegment:
        segments = self._segments(text)
        if len(segments) != 1:
            raise ValueError(
                "synthesize() requires text that resolves to one segment; use synthesize_to_file() for multi-segment text"
            )
        return segments[0]

    def _postprocess(self, path: Path) -> None:
        if self.audio_processing is not None:
            postprocess_audio_file(path, self.audio_processing)


async def _save_async_audio_stream(audio_data: AsyncIterator[bytes], file_path: Path) -> None:
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "wb") as f:
        async for chunk in audio_data:
            await asyncio.to_thread(f.write, chunk)
