import io
import numpy as np
import soundfile as sf
from par_tts.amplitude import amplitude_envelope


def _wav(samples: np.ndarray, sr: int = 24000) -> bytes:
    buf = io.BytesIO()
    sf.write(buf, samples.astype(np.int16), sr, format="WAV")
    return buf.getvalue()


def test_silence_is_near_zero():
    wav = _wav(np.zeros(24000, dtype=np.int16))
    env = amplitude_envelope(wav, 24000, hop_ms=16.0)
    assert all(level < 0.02 for _, level in env)
    assert len(env) >= 40  # ~1s / 16ms


def test_loud_signal_is_near_one():
    wav = _wav((np.sin(np.linspace(0, 200, 24000)) * 30000).astype(np.int16))
    env = amplitude_envelope(wav, 24000, hop_ms=16.0)
    assert max(level for _, level in env) > 0.8


def test_timestamps_are_hop_spaced_and_monotonic():
    wav = _wav(np.zeros(24000, dtype=np.int16))
    env = amplitude_envelope(wav, 24000, hop_ms=16.0)
    ts = [t for t, _ in env]
    assert ts == sorted(ts)
    assert abs(ts[1] - ts[0] - 16.0) < 1.5
