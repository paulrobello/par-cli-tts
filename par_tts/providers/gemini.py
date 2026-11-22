"""Google Gemini TTS provider implementation.

Uses stateless Interactions requests for Gemini 3.8 TTS and generateContent
for explicitly selected legacy models. Both paths return a complete WAV file.
"""

import base64
import logging
import struct
from typing import Any

from par_tts.defaults import DEFAULT_GEMINI_MODEL, DEFAULT_GEMINI_VOICE
from par_tts.http_client import create_http_client
from par_tts.providers.base import TTSProvider, Voice
from par_tts.retry import run_with_retries

_logger = logging.getLogger(__name__)

GEMINI_API_BASE = "https://generativelanguage.googleapis.com/v1beta"
_INTERACTIONS_MODELS = frozenset({"gemini-3.8-flash-lite-tts", "gemini-3.8-flash-tts"})

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


def _interaction_wav(payload: dict[str, Any]) -> bytes:
    """Extract the last generated audio block, which is already a WAV file."""
    wav_error = "Gemini Interactions did not return WAV audio"
    for step in reversed(payload.get("steps") or []):
        if step.get("type") != "model_output":
            continue
        for part in reversed(step.get("content") or []):
            if part.get("type") == "audio" and part.get("data"):
                try:
                    audio = base64.b64decode(part["data"], validate=True)
                except (ValueError, TypeError) as exc:
                    raise RuntimeError(wav_error) from exc
                if not (audio.startswith(b"RIFF") and audio[8:12] == b"WAVE"):
                    raise RuntimeError(wav_error)
                return audio
    raise RuntimeError(wav_error)


class GeminiProvider(TTSProvider):
    """Google Gemini TTS provider."""

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

        uses_interactions = active_model in _INTERACTIONS_MODELS
        if uses_interactions:
            url = f"{GEMINI_API_BASE}/interactions"
            body: dict[str, Any] = {
                "model": active_model,
                "input": [{"type": "user_input", "content": [{"type": "text", "text": text}]}],
                "response_format": {"type": "audio"},
                "generation_config": {"speech_config": [{"voice": canonical_voice}]},
                "store": False,
            }
        else:
            url = f"{GEMINI_API_BASE}/models/{active_model}:generateContent"
            body = {
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
        headers = {
            "x-goog-api-key": self.api_key or "",
            "Content-Type": "application/json",
        }

        resp = run_with_retries(
            lambda: self.client.post(url, headers=headers, json=body),
            self.retry_policy,
            operation="Gemini speech generation",
        )
        if resp.status_code != 200:
            # Sanitize response text to avoid leaking API key in error messages
            error_text = resp.text[:500]
            if self.api_key and self.api_key in error_text:
                error_text = error_text.replace(self.api_key, "[REDACTED]")
            raise RuntimeError(f"Gemini API error {resp.status_code}: {error_text}")

        payload = resp.json()
        if uses_interactions:
            return _interaction_wav(payload)

        try:
            inline = payload["candidates"][0]["content"]["parts"][0]["inlineData"]
            pcm_b64 = inline["data"]
        except (KeyError, IndexError, TypeError) as e:
            raise RuntimeError(f"Unexpected Gemini response shape: {payload}") from e

        pcm = base64.b64decode(pcm_b64)
        return wrap_pcm_as_wav(pcm)

    def list_voices(self) -> list[Voice]:
        """Return all 30 prebuilt Gemini TTS voices.

        Returns:
            List of Voice objects with id and name set to the canonical
            voice name, labels containing the style descriptor, and
            category set to "Gemini TTS".
        """
        return [Voice(id=name, name=name, labels=[style], category="Gemini TTS") for name, style in _GEMINI_VOICES]

    def resolve_voice(self, voice_identifier: str) -> str:
        """Resolve a voice name to its canonical Gemini voice name.

        Voice names are case-insensitive.  If the input exactly matches
        (ignoring case) a known voice, the canonical form is returned.
        Falls back to a single-result partial substring match.

        Args:
            voice_identifier: Voice name to resolve (e.g. ``"kore"``).

        Returns:
            Canonical voice name (e.g. ``"Kore"``).

        Raises:
            ValueError: If the voice name matches zero or multiple voices.
        """
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
