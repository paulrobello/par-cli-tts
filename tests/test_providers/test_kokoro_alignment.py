# tests/test_providers/test_kokoro_alignment.py
import numpy as np
import pytest

from par_tts.providers.base import KokoroAlignment
from par_tts.providers.kokoro_onnx import KokoroONNXProvider


class FakeTokenizer:
    def phonemize(self, text, lang): return "həloʊ"
    def tokenize(self, phonemes): return [1, 2, 3]


class FakeSession:
    """Mimics kokoro_onnx's timestamped session: run(None, inputs) -> [waveform, durations]."""
    def get_outputs(self):
        class O:
            def __init__(self, n): self.name = n
        return [O("waveform"), O("durations")]
    def run(self, outnames, inputs):
        audio = np.zeros(24000 * 2, dtype=np.float32)  # 2s
        pred_dur = np.array([10, 20, 30], dtype=np.int64)
        return [audio, pred_dur]


def test_alignment_returns_visemes(monkeypatch):
    # Build a provider without loading the real Kokoro by stubbing __init__'s model load.
    prov = KokoroONNXProvider.__new__(KokoroONNXProvider)
    prov.kokoro = type("K", (), {})()
    prov.kokoro.tokenizer = FakeTokenizer()
    prov.kokoro.get_voice_style = lambda name: np.zeros((512, 1, 256), dtype=np.float32)
    prov.kokoro.get_voices = lambda: ["af_heart"]
    prov._timestamped_sess = FakeSession()           # injected — skips real load
    prov.model_path = ""; prov.voice_path = ""

    align = prov.generate_speech_with_alignment("hello", voice="af_heart")
    assert isinstance(align, KokoroAlignment)
    assert align.sample_rate == 24000
    assert len(align.phonemes) == 3
    assert len(align.visemes) == 3
    assert align.visemes[0].start_ms == 0.0


def test_real_alignment_runs_or_skips():
    from par_tts.model_downloader import ModelDownloader
    if not ModelDownloader().get_timestamped_model_path().exists():
        pytest.skip("timestamped model absent")
    try:
        prov = KokoroONNXProvider()
    except Exception:
        pytest.skip("kokoro provider/model unavailable")
    try:
        align = prov.generate_speech_with_alignment("hello world", voice="af_heart")
    except FileNotFoundError:
        pytest.skip("timestamped model missing at runtime")
    assert len(align.visemes) > 0
    assert align.visemes[-1].end_ms > 0
    assert align.sample_rate == 24000
    # Trim (default) removes Kokoro's leading silence and shifts visemes to match:
    # no negative starts, and the trimmed audio is shorter than the untrimmed.
    assert all(v.start_ms >= 0 for v in align.visemes)
    untrimmed = prov.generate_speech_with_alignment("hello world", voice="af_heart", trim=False)
    assert len(align.audio) < len(untrimmed.audio)
    assert untrimmed.visemes[0].start_ms == 0.0
