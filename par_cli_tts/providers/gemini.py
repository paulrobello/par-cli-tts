"""Google Gemini TTS provider implementation.

Uses the Gemini API's `generateContent` endpoint with `responseModalities: ["AUDIO"]`
to perform single-speaker text-to-speech. The API returns raw signed 16-bit PCM
audio at 24 kHz mono, base64-encoded inside the JSON response. This provider
decodes that, prepends a 44-byte WAV header, and hands the result back as a
single-shot ``bytes`` payload (the response is not chunked).
"""

import base64
import logging
import struct
from collections.abc import Iterator
from pathlib import Path
from typing import Any

from par_cli_tts.audio import play_audio_bytes
from par_cli_tts.defaults import DEFAULT_GEMINI_VOICE
from par_cli_tts.http_client import create_http_client
from par_cli_tts.providers.base import TTSProvider, Voice

_logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta/models"
DEFAULT_GEMINI_MODEL = "gemini-2.5-flash-preview-tts"

PCM_SAMPLE_RATE = 24000
PCM_CHANNELS = 1
PCM_BITS_PER_SAMPLE = 16


# (voice_name, style_descriptor)
_GEMINI_VOICES: tuple[tuple[str, str], ...] = (
    ("Zephyr", "Bright"),
    ("Puck", "Upbeat"),
    ("Charon", "Informative"),
    ("Kore", "Firm"),
    ("Fenrir", "Excitable"),
    ("Leda", "Youthful"),
    ("Orus", "Firm"),
    ("Aoede", "Breezy"),
    ("Callirrhoe", "Easy-going"),
    ("Autonoe", "Bright"),
    ("Enceladus", "Breathy"),
    ("Iapetus", "Clear"),
    ("Umbriel", "Easy-going"),
    ("Algieba", "Smooth"),
    ("Despina", "Smooth"),
    ("Erinome", "Clear"),
    ("Algenib", "Gravelly"),
    ("Rasalgethi", "Informative"),
    ("Laomedeia", "Upbeat"),
    ("Achernar", "Soft"),
    ("Alnilam", "Firm"),
    ("Schedar", "Even"),
    ("Gacrux", "Mature"),
    ("Pulcherrima", "Forward"),
    ("Achird", "Friendly"),
    ("Zubenelgenubi", "Casual"),
    ("Vindemiatrix", "Gentle"),
    ("Sadachbia", "Lively"),
    ("Sadaltager", "Knowledgeable"),
    ("Sulafat", "Warm"),
)


def wrap_pcm_as_wav(
    pcm: bytes,
    sample_rate: int = PCM_SAMPLE_RATE,
    channels: int = PCM_CHANNELS,
    bits_per_sample: int = PCM_BITS_PER_SAMPLE,
) -> bytes:
    """Prepend a 44-byte RIFF/WAVE header to raw little-endian PCM data."""
    byte_rate = sample_rate * channels * bits_per_sample // 8
    block_align = channels * bits_per_sample // 8
    data_size = len(pcm)
    header = b"".join(
        (
            b"RIFF",
            struct.pack("<I", 36 + data_size),
            b"WAVE",
            b"fmt ",
            struct.pack("<I", 16),
            struct.pack("<H", 1),  # PCM format
            struct.pack("<H", channels),
            struct.pack("<I", sample_rate),
            struct.pack("<I", byte_rate),
            struct.pack("<H", block_align),
            struct.pack("<H", bits_per_sample),
            b"data",
            struct.pack("<I", data_size),
        )
    )
    return header + pcm


class GeminiProvider(TTSProvider):
    """Google Gemini TTS provider (preview)."""

    VOICE_NAMES = frozenset(name for name, _ in _GEMINI_VOICES)
    _VOICE_CANONICAL = {name.lower(): name for name, _ in _GEMINI_VOICES}

    def __init__(self, api_key: str, **kwargs: Any):
        """Initialize the Gemini TTS provider.

        Args:
            api_key: Google AI Studio (Gemini) API key.
            **kwargs: Additional configuration (e.g. `timeout`).
        """
        super().__init__(api_key, **kwargs)
        self.client = create_http_client(timeout=kwargs.get("timeout", 60.0))

    @property
    def name(self) -> str:
        return "Gemini"

    @property
    def supported_formats(self) -> list[str]:
        # API only emits raw PCM; we always wrap to WAV for the user.
        return ["wav"]

    @property
    def default_model(self) -> str:
        return DEFAULT_GEMINI_MODEL

    @property
    def default_voice(self) -> str:
        return DEFAULT_GEMINI_VOICE

    def generate_speech(
        self,
        text: str,
        voice: str,
        model: str | None = None,
        **kwargs: Any,
    ) -> bytes:
        """Synthesize speech as a self-contained WAV byte string.

        Args:
            text: Text to convert to speech.
            voice: Prebuilt voice name (e.g. "Kore", "Zephyr"). Case-insensitive
                input; the canonical form is sent to the API.
            model: Optional Gemini TTS model override.
            **kwargs: Ignored; accepted for cross-provider compatibility.
        """
        del kwargs
        active_model = model or self.default_model
        canonical_voice = self._VOICE_CANONICAL.get(voice.lower(), voice)

        url = f"{GEMINI_API_BASE}/{active_model}:generateContent"
        headers = {
            "x-goog-api-key": self.api_key or "",
            "Content-Type": "application/json",
        }
        body: dict[str, Any] = {
            "contents": [{"parts": [{"text": text}]}],
            "generationConfig": {
                "responseModalities": ["AUDIO"],
                "speechConfig": {
                    "voiceConfig": {
                        "prebuiltVoiceConfig": {"voiceName": canonical_voice},
                    },
                },
            },
        }

        resp = self.client.post(url, headers=headers, json=body)
        if resp.status_code != 200:
            raise RuntimeError(f"Gemini API error {resp.status_code}: {resp.text[:500]}")

        payload = resp.json()
        try:
            inline = payload["candidates"][0]["content"]["parts"][0]["inlineData"]
            pcm_b64 = inline["data"]
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Unexpected Gemini response shape: {payload}") from e

        pcm = base64.b64decode(pcm_b64)
        return wrap_pcm_as_wav(pcm)

    def list_voices(self) -> list[Voice]:
        return [Voice(id=name, name=name, labels=[style], category="Gemini TTS") for name, style in _GEMINI_VOICES]

    def resolve_voice(self, voice_identifier: str) -> str:
        ident = voice_identifier.strip().lower()
        if ident in self._VOICE_CANONICAL:
            canonical = self._VOICE_CANONICAL[ident]
            if canonical != voice_identifier:
                _logger.info("Resolved '%s' to voice: %s", voice_identifier, canonical)
            return canonical

        # Last-resort partial match (single hit only)
        partial = [name for name in self.VOICE_NAMES if ident in name.lower()]
        if len(partial) == 1:
            _logger.info("Resolved '%s' to voice: %s", voice_identifier, partial[0])
            return partial[0]

        raise ValueError(f"Voice '{voice_identifier}' not found. Available: {', '.join(sorted(self.VOICE_NAMES))}")

    def save_audio(self, audio_data: bytes | Iterator[bytes], file_path: str | Path) -> None:
        path = Path(file_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(audio_data, bytes):
            path.write_bytes(audio_data)
        else:
            self.stream_to_file(audio_data, path)

    def play_audio(self, audio_data: bytes | Iterator[bytes], volume: float = 1.0) -> None:
        if not isinstance(audio_data, bytes):
            audio_data = b"".join(audio_data)
        play_audio_bytes(audio_data, volume=volume, suffix=".wav")
