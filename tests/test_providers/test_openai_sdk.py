"""Verify the real OpenAI SDK speech request against a local mock transport."""

from __future__ import annotations

import importlib
import json
from importlib.metadata import version
from typing import Any

import pytest
from openai import OpenAI

from par_tts.providers import openai as provider_module


@pytest.mark.parametrize(
    ("model", "speed", "expected_speed", "expected_instructions"),
    [
        ("gpt-4o-mini-tts", 6.0, 4.0, "Speak softly."),
        ("tts-1", 0.1, 0.25, None),
    ],
)
def test_speech_sdk_request(
    monkeypatch: pytest.MonkeyPatch,
    model: str,
    speed: float,
    expected_speed: float,
    expected_instructions: str | None,
) -> None:
    """Exercise SDK 2/3 serialization and audio decoding without a network call."""
    http = importlib.import_module("httpx2" if version("openai").startswith("3.") else "httpx")
    requests: list[Any] = []

    def respond(request: Any) -> Any:
        requests.append(request)
        return http.Response(200, content=b"mock audio", headers={"Content-Type": "audio/wav"})

    with http.Client(transport=http.MockTransport(respond)) as client:

        def make_client(**kwargs: Any) -> OpenAI:
            # A provider-created HTTP client could belong to the wrong SDK transport.
            assert kwargs == {"api_key": "test-key", "timeout": 2.5}
            return OpenAI(base_url="https://tts.invalid/v1", http_client=client, **kwargs)

        monkeypatch.setattr(provider_module, "OpenAI", make_client)
        provider = provider_module.OpenAIProvider("test-key", timeout=2.5)
        audio = provider.generate_speech(
            "Hello",
            voice="alloy",
            model=model,
            response_format="wav",
            speed=speed,
            instructions="Speak softly.",
        )

    assert audio == b"mock audio"
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "POST"
    assert request.url.path == "/v1/audio/speech"
    assert request.headers["Authorization"] == "Bearer test-key"
    expected = {
        "model": model,
        "voice": "alloy",
        "input": "Hello",
        "response_format": "wav",
        "speed": expected_speed,
    }
    if expected_instructions is not None:
        expected["instructions"] = expected_instructions
    assert json.loads(request.content) == expected
