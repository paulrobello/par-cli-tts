"""Base class for TTS providers."""

from __future__ import annotations

import asyncio
import inspect
import time
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Awaitable, Callable, Iterator
from dataclasses import asdict, dataclass, is_dataclass
from pathlib import Path
from typing import Any, TypeAlias

from par_tts.retry import RetryPolicy

AudioData: TypeAlias = bytes | Iterator[bytes]
AsyncAudioData: TypeAlias = bytes | AsyncIterator[bytes]
CallbackResult: TypeAlias = None | Awaitable[None]
ChunkCallback: TypeAlias = Callable[[bytes], CallbackResult]
ProgressCallback: TypeAlias = Callable[["SpeechProgress"], CallbackResult]
CompleteCallback: TypeAlias = Callable[["SpeechComplete"], CallbackResult]
ErrorCallback: TypeAlias = Callable[[Exception], CallbackResult]


@dataclass
class Voice:
    """Represents a TTS voice.

    Attributes:
        id: Provider-specific voice identifier (e.g. ``"aura-2-thalia-en"``).
        name: Human-readable voice name (e.g. ``"Thalia"``).
        labels: Optional tags describing voice traits (language, accent, style).
        category: Optional grouping label (e.g. ``"Deepgram Aura-2 (en)"``).
    """

    id: str
    name: str
    labels: list[str] | None = None
    category: str | None = None


@dataclass(frozen=True)
class ProviderCapabilities:
    """Static provider capability metadata used without instantiation."""

    formats: list[str]
    supports_speed: bool = False
    supports_streaming: bool = False
    supports_voice_controls: bool = False
    supports_instructions: bool = False
    supports_sample_rate: bool = False


@dataclass(frozen=True)
class ProviderPlugin:
    """Provider plugin descriptor.

    Descriptors are intentionally static so commands like ``--capabilities`` can
    inspect providers without requiring API keys or creating network clients.
    """

    name: str
    provider_class: type[TTSProvider]
    description: str
    capabilities: ProviderCapabilities
    default_model: str
    default_voice: str | None = None
    requires_api_key: bool = True
    api_key_env_vars: tuple[str, ...] = ()
    source: str = "builtin"
    cost_per_million_chars: float | None = None


@dataclass(frozen=True)
class SpeechProgress:
    """Progress emitted while speech audio is generated or consumed."""

    provider: str
    text_chars: int
    bytes_generated: int
    chunks_generated: int
    stage: str = "generating"


@dataclass(frozen=True)
class SpeechComplete:
    """Completion metadata emitted after speech audio has been consumed."""

    provider: str
    text_chars: int
    bytes_generated: int
    chunks_generated: int
    elapsed_seconds: float


@dataclass(frozen=True)
class SpeechCallbacks:
    """Optional hooks for observing speech generation.

    Callbacks may be regular functions or async functions. Synchronous library
    methods run async callbacks with ``asyncio.run()`` when no event loop is
    active, or schedule them on the running loop when one exists.
    """

    on_chunk: ChunkCallback | None = None
    on_progress: ProgressCallback | None = None
    on_complete: CompleteCallback | None = None
    on_error: ErrorCallback | None = None


class TTSProvider(ABC):
    """Abstract base class for TTS providers."""

    # Subclasses override this to declare which kwargs they accept for
    # ``generate_speech()``.  Keys are kwarg names; values are defaults.
    # The CLI uses this mapping to build provider-specific option dicts
    # without if/elif chains.
    PROVIDER_KWARGS: dict[str, Any] = {}

    def __init__(self, api_key: str | None = None, **kwargs: Any):
        """
        Initialize the TTS provider.

        Args:
            api_key: Optional API key for the provider. Some providers (like offline ones) don't need it.
            **kwargs: Additional provider-specific configuration.
        """
        self.api_key = api_key
        self.retry_policy = RetryPolicy(
            retry_attempts=int(kwargs.get("retry_attempts", 0)),
            backoff_seconds=float(kwargs.get("retry_backoff", 0.0)),
        )

    @abstractmethod
    def generate_speech(
        self,
        text: str,
        voice: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> bytes | Iterator[bytes]:
        """
        Generate speech from text.

        Args:
            text: Text to convert to speech.
            voice: Voice ID or name to use.
            model: Optional model to use (provider-specific).
            **kwargs: Additional provider-specific parameters.

        Returns:
            Audio data as bytes or an iterator of bytes for streaming.
        """
        pass

    @abstractmethod
    def list_voices(self) -> list[Voice]:
        """
        List available voices.

        Returns:
            List of available Voice objects.
        """
        pass

    async def generate_speech_async(
        self,
        text: str,
        voice: str,
        model: str | None = None,
        callbacks: SpeechCallbacks | None = None,
        **kwargs: Any,
    ) -> AsyncAudioData:
        """Async equivalent of ``generate_speech()``.

        Synchronous provider implementations run in a worker thread. Iterator
        responses are exposed as async iterators so streamed providers do not
        block the event loop while chunks are consumed.
        """
        start_time = time.perf_counter()
        try:
            audio_data = await asyncio.to_thread(self.generate_speech, text, voice, model, **kwargs)
        except Exception as exc:
            await _emit_error_async(callbacks, exc)
            raise

        if isinstance(audio_data, bytes):
            await _emit_bytes_callbacks_async(callbacks, audio_data, self.name, len(text), start_time)
            return audio_data

        return _wrap_iterator_async(audio_data, callbacks, self.name, len(text), start_time)

    async def list_voices_async(self) -> list[Voice]:
        """Async equivalent of ``list_voices()``."""
        return await asyncio.to_thread(self.list_voices)

    @abstractmethod
    def resolve_voice(self, voice_identifier: str) -> str:
        """
        Resolve a voice name or ID to a valid voice ID.

        Args:
            voice_identifier: Voice name or ID to resolve.

        Returns:
            Valid voice ID for the provider.

        Raises:
            ValueError: If voice cannot be resolved.
        """
        pass

    def save_audio(self, audio_data: bytes | Iterator[bytes], file_path: str | Path) -> None:
        """Save audio data to a file.

        Handles both bytes and iterator inputs.  Providers that need
        special handling (e.g. ElevenLabs SDK ``save``) can override.

        Args:
            audio_data: Audio data to save (bytes or iterator for streaming).
            file_path: Path to save the audio file.
        """
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(audio_data, bytes):
            path.write_bytes(audio_data)
        else:
            self.stream_to_file(audio_data, path)

    def stream_to_file(self, audio_stream: Iterator[bytes], file_path: str | Path) -> None:
        """
        Stream audio data directly to file without buffering in memory.

        Args:
            audio_stream: Iterator yielding audio data chunks.
            file_path: Path to save the audio file.
        """
        from par_tts.utils import stream_to_file

        stream_to_file(audio_stream, file_path)

    def play_audio(self, audio_data: bytes | Iterator[bytes], volume: float = 1.0) -> None:
        """Play audio data with volume control.

        Converts iterator to bytes if needed, then plays via the system
        audio player.  Providers can override for custom playback.

        Args:
            audio_data: Audio data to play (bytes or iterator).
            volume: Volume level (0.0 = silent, 1.0 = normal, 2.0 = double volume).
        """
        from par_tts.audio import play_audio_bytes

        if not isinstance(audio_data, bytes):
            audio_data = b"".join(audio_data)

        # Determine file suffix from supported formats (first entry is default).
        suffix = f".{self.supported_formats[0]}" if self.supported_formats else ".mp3"
        play_audio_bytes(audio_data, volume=volume, suffix=suffix)

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @property
    @abstractmethod
    def supported_formats(self) -> list[str]:
        """List of supported audio formats."""
        pass

    @property
    @abstractmethod
    def default_model(self) -> str:
        """Default model for this provider."""
        pass

    @property
    @abstractmethod
    def default_voice(self) -> str:
        """Default voice for this provider."""
        pass


def apply_speech_callbacks(
    audio_data: AudioData,
    callbacks: SpeechCallbacks | None,
    *,
    provider: str,
    text_chars: int,
    start_time: float | None = None,
) -> AudioData:
    """Return audio data wrapped with callback emission."""
    active_start = start_time if start_time is not None else time.perf_counter()
    if isinstance(audio_data, bytes):
        _emit_bytes_callbacks(callbacks, audio_data, provider, text_chars, active_start)
        return audio_data
    return _wrap_iterator(audio_data, callbacks, provider, text_chars, active_start)


def emit_error_callback(callbacks: SpeechCallbacks | None, exc: Exception) -> None:
    """Emit an error callback from synchronous code."""
    if callbacks and callbacks.on_error:
        _run_callback(callbacks.on_error, exc)


@dataclass
class ElevenLabsOptions:
    """ElevenLabs-specific generation options."""

    stability: float = 0.5
    similarity_boost: float = 0.5

    def __post_init__(self) -> None:
        _validate_range("stability", self.stability, 0.0, 1.0)
        _validate_range("similarity_boost", self.similarity_boost, 0.0, 1.0)


@dataclass
class OpenAIOptions:
    """OpenAI-specific generation options."""

    speed: float = 1.0
    response_format: str = "mp3"
    instructions: str | None = None

    def __post_init__(self) -> None:
        _validate_range("speed", self.speed, 0.25, 4.0)
        _validate_choice("response_format", self.response_format, {"mp3", "opus", "aac", "flac", "wav", "pcm"})


@dataclass
class KokoroOptions:
    """Kokoro ONNX-specific generation options."""

    speed: float = 1.0
    lang: str = "en-us"
    output_format: str = "wav"

    def __post_init__(self) -> None:
        _validate_range("speed", self.speed, 0.25, 4.0)
        _validate_choice("output_format", self.output_format, {"wav", "flac", "ogg"})


@dataclass
class DeepgramOptions:
    """Deepgram-specific generation options."""

    response_format: str = "mp3"
    sample_rate: int | None = None

    def __post_init__(self) -> None:
        _validate_choice("response_format", self.response_format, {"mp3", "wav", "flac", "opus", "aac"})
        if self.sample_rate is not None and self.sample_rate <= 0:
            raise ValueError("sample_rate must be greater than 0")


@dataclass
class GeminiOptions:
    """Gemini-specific generation options.

    The Gemini TTS preview API currently offers no tunable generation
    parameters beyond voice and model selection.  This dataclass is
    reserved for future options (e.g. speaking_rate when the API adds it).
    """

    pass


ProviderOptions: TypeAlias = ElevenLabsOptions | OpenAIOptions | KokoroOptions | DeepgramOptions | GeminiOptions
ProviderOptionSchema: TypeAlias = (
    type[ElevenLabsOptions] | type[OpenAIOptions] | type[KokoroOptions] | type[DeepgramOptions] | type[GeminiOptions]
)

PROVIDER_OPTION_SCHEMAS: dict[str, ProviderOptionSchema] = {
    "elevenlabs": ElevenLabsOptions,
    "openai": OpenAIOptions,
    "kokoro-onnx": KokoroOptions,
    "deepgram": DeepgramOptions,
    "gemini": GeminiOptions,
}


def get_provider_option_schema(provider: str) -> ProviderOptionSchema:
    """Return the typed option dataclass for a provider name."""
    try:
        return PROVIDER_OPTION_SCHEMAS[provider]
    except KeyError as exc:
        raise ValueError(
            f"Unknown provider '{provider}'. Available: {', '.join(sorted(PROVIDER_OPTION_SCHEMAS))}"
        ) from exc


def options_to_kwargs(options: ProviderOptions | dict[str, Any], *, include_none: bool = False) -> dict[str, Any]:
    """Convert typed provider options to ``generate_speech`` keyword arguments."""
    if isinstance(options, dict):
        data = dict(options)
    elif is_dataclass(options) and not isinstance(options, type):
        data = asdict(options)
    else:
        raise TypeError("options must be a provider options dataclass or dict")
    if include_none:
        return data
    return {key: value for key, value in data.items() if value is not None}


def _validate_range(name: str, value: float, minimum: float, maximum: float) -> None:
    if value < minimum or value > maximum:
        raise ValueError(f"{name} must be between {minimum} and {maximum}")


def _validate_choice(name: str, value: str, choices: set[str]) -> None:
    if value not in choices:
        raise ValueError(f"{name} must be one of: {', '.join(sorted(choices))}")


def _emit_bytes_callbacks(
    callbacks: SpeechCallbacks | None,
    audio_data: bytes,
    provider: str,
    text_chars: int,
    start_time: float,
) -> None:
    if callbacks is None:
        return
    bytes_generated = len(audio_data)
    if callbacks.on_chunk:
        _run_callback(callbacks.on_chunk, audio_data)
    if callbacks.on_progress:
        _run_callback(
            callbacks.on_progress,
            SpeechProgress(
                provider=provider,
                text_chars=text_chars,
                bytes_generated=bytes_generated,
                chunks_generated=1,
            ),
        )
    if callbacks.on_complete:
        _run_callback(
            callbacks.on_complete,
            SpeechComplete(
                provider=provider,
                text_chars=text_chars,
                bytes_generated=bytes_generated,
                chunks_generated=1,
                elapsed_seconds=time.perf_counter() - start_time,
            ),
        )


def _wrap_iterator(
    audio_stream: Iterator[bytes],
    callbacks: SpeechCallbacks | None,
    provider: str,
    text_chars: int,
    start_time: float,
) -> Iterator[bytes]:
    bytes_generated = 0
    chunks_generated = 0
    try:
        for chunk in audio_stream:
            chunks_generated += 1
            bytes_generated += len(chunk)
            if callbacks and callbacks.on_chunk:
                _run_callback(callbacks.on_chunk, chunk)
            if callbacks and callbacks.on_progress:
                _run_callback(
                    callbacks.on_progress,
                    SpeechProgress(
                        provider=provider,
                        text_chars=text_chars,
                        bytes_generated=bytes_generated,
                        chunks_generated=chunks_generated,
                    ),
                )
            yield chunk
    except Exception as exc:
        emit_error_callback(callbacks, exc)
        raise
    if callbacks and callbacks.on_complete:
        _run_callback(
            callbacks.on_complete,
            SpeechComplete(
                provider=provider,
                text_chars=text_chars,
                bytes_generated=bytes_generated,
                chunks_generated=chunks_generated,
                elapsed_seconds=time.perf_counter() - start_time,
            ),
        )


async def _emit_bytes_callbacks_async(
    callbacks: SpeechCallbacks | None,
    audio_data: bytes,
    provider: str,
    text_chars: int,
    start_time: float,
) -> None:
    if callbacks is None:
        return
    bytes_generated = len(audio_data)
    if callbacks.on_chunk:
        await _run_callback_async(callbacks.on_chunk, audio_data)
    if callbacks.on_progress:
        await _run_callback_async(
            callbacks.on_progress,
            SpeechProgress(
                provider=provider,
                text_chars=text_chars,
                bytes_generated=bytes_generated,
                chunks_generated=1,
            ),
        )
    if callbacks.on_complete:
        await _run_callback_async(
            callbacks.on_complete,
            SpeechComplete(
                provider=provider,
                text_chars=text_chars,
                bytes_generated=bytes_generated,
                chunks_generated=1,
                elapsed_seconds=time.perf_counter() - start_time,
            ),
        )


async def _wrap_iterator_async(
    audio_stream: Iterator[bytes],
    callbacks: SpeechCallbacks | None,
    provider: str,
    text_chars: int,
    start_time: float,
) -> AsyncIterator[bytes]:
    bytes_generated = 0
    chunks_generated = 0
    try:
        while True:
            chunk = await asyncio.to_thread(_next_chunk, audio_stream)
            if chunk is None:
                break
            chunks_generated += 1
            bytes_generated += len(chunk)
            if callbacks and callbacks.on_chunk:
                await _run_callback_async(callbacks.on_chunk, chunk)
            if callbacks and callbacks.on_progress:
                await _run_callback_async(
                    callbacks.on_progress,
                    SpeechProgress(
                        provider=provider,
                        text_chars=text_chars,
                        bytes_generated=bytes_generated,
                        chunks_generated=chunks_generated,
                    ),
                )
            yield chunk
    except Exception as exc:
        await _emit_error_async(callbacks, exc)
        raise
    if callbacks and callbacks.on_complete:
        await _run_callback_async(
            callbacks.on_complete,
            SpeechComplete(
                provider=provider,
                text_chars=text_chars,
                bytes_generated=bytes_generated,
                chunks_generated=chunks_generated,
                elapsed_seconds=time.perf_counter() - start_time,
            ),
        )


def _next_chunk(audio_stream: Iterator[bytes]) -> bytes | None:
    try:
        return next(audio_stream)
    except StopIteration:
        return None


def _run_callback(callback: Callable[[Any], CallbackResult], value: Any) -> None:
    result = callback(value)
    if not inspect.isawaitable(result):
        return
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run(_await_callback_result(result))
    else:
        loop.create_task(_await_callback_result(result))


async def _await_callback_result(result: Awaitable[None]) -> None:
    await result


async def _run_callback_async(callback: Callable[[Any], CallbackResult], value: Any) -> None:
    result = callback(value)
    if inspect.isawaitable(result):
        await result


async def _emit_error_async(callbacks: SpeechCallbacks | None, exc: Exception) -> None:
    if callbacks and callbacks.on_error:
        await _run_callback_async(callbacks.on_error, exc)
