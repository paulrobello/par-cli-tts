"""Offline HTTP contract coverage for Gemini speech generation."""

from __future__ import annotations

import base64
import io
import json
import wave
from unittest.mock import patch

import httpx
import pytest

from par_tts.providers.gemini import GeminiProvider

_PCM = b"\x00\x00\x01\x00"


def _wav() -> bytes:
    stream = io.BytesIO()
    with wave.open(stream, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(24_000)
        wav.writeframes(_PCM)
    return stream.getvalue()


@pytest.mark.parametrize("model", [None, "gemini-3.8-flash-tts"])
def test_interactions_sends_stateless_speech_and_preserves_wav(model: str | None) -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1beta/interactions"
        assert request.headers["x-goog-api-key"] == "test-key"
        assert json.loads(request.content) == {
            "model": model or "gemini-3.8-flash-lite-tts",
            "input": [{"type": "user_input", "content": [{"type": "text", "text": "Hello"}]}],
            "response_format": {"type": "audio"},
            "generation_config": {"speech_config": [{"voice": "Kore"}]},
            "store": False,
        }
        return httpx.Response(
            200,
            json={
                "steps": [
                    {"type": "user_input", "content": [{"type": "text", "text": "Hello"}]},
                    {
                        "type": "model_output",
                        "content": [
                            {"type": "audio", "data": base64.b64encode(_wav()).decode()},
                            {"type": "text", "text": "Ignored"},
                        ],
                    },
                ],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with patch("par_tts.providers.gemini.create_http_client", return_value=client):
            assert GeminiProvider("test-key").generate_speech("Hello", "kore", model=model) == _wav()


def test_explicit_preview_model_still_uses_generate_content() -> None:
    def respond(request: httpx.Request) -> httpx.Response:
        assert request.url.path == "/v1beta/models/gemini-2.5-flash-preview-tts:generateContent"
        payload = json.loads(request.content)
        assert payload["generationConfig"]["responseModalities"] == ["AUDIO"]
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {
                        "content": {
                            "parts": [
                                {"inlineData": {"data": base64.b64encode(_PCM).decode()}},
                            ]
                        }
                    }
                ],
            },
        )

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        with patch("par_tts.providers.gemini.create_http_client", return_value=client):
            assert (
                GeminiProvider("test-key").generate_speech("Hello", "Kore", model="gemini-2.5-flash-preview-tts")
                == _wav()
            )


def test_interactions_missing_audio_is_a_clear_error() -> None:
    response = httpx.Response(200, json={"steps": [{"type": "model_output", "content": []}]})
    with httpx.Client(transport=httpx.MockTransport(lambda _: response)) as client:
        with patch("par_tts.providers.gemini.create_http_client", return_value=client):
            with pytest.raises(RuntimeError, match="did not return WAV audio"):
                GeminiProvider("test-key").generate_speech("Hello", "Kore")
