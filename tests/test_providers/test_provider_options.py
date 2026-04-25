"""Tests for per-provider options."""

import pytest

from par_tts.providers.base import (
    DeepgramOptions,
    ElevenLabsOptions,
    GeminiOptions,
    KokoroOptions,
    OpenAIOptions,
)


class TestPerProviderOptions:
    @pytest.mark.parametrize(
        "cls,defaults",
        [
            (ElevenLabsOptions, {"stability": 0.5, "similarity_boost": 0.5}),
            (OpenAIOptions, {"speed": 1.0, "response_format": "mp3"}),
            (KokoroOptions, {"speed": 1.0, "lang": "en-us", "output_format": "wav"}),
            (DeepgramOptions, {"response_format": "mp3", "sample_rate": None}),
            (GeminiOptions, {}),
        ],
    )
    def test_defaults(self, cls, defaults):
        opts = cls()
        for field_name, expected in defaults.items():
            assert getattr(opts, field_name) == expected

    def test_elevenlabs_options_custom(self):
        opts = ElevenLabsOptions(stability=0.8, similarity_boost=0.3)
        assert opts.stability == 0.8

    def test_openai_options_with_instructions(self):
        opts = OpenAIOptions(instructions="Speak cheerfully")
        assert opts.instructions == "Speak cheerfully"

    def test_kokoro_options_custom(self):
        opts = KokoroOptions(speed=1.5, lang="fr-fr")
        assert opts.speed == 1.5
        assert opts.lang == "fr-fr"

    def test_deepgram_options_sample_rate(self):
        opts = DeepgramOptions(sample_rate=16000)
        assert opts.sample_rate == 16000

    def test_all_options_are_dataclasses(self):
        for cls in (ElevenLabsOptions, OpenAIOptions, KokoroOptions, DeepgramOptions, GeminiOptions):
            assert hasattr(cls, "__dataclass_fields__")
