"""Mouth-open envelope from PCM audio — the amplitude-driven viseme fallback.

Generic: works on any audio, not just Kokoro. Produces a mouth-open level in
[0, 1] sampled every `hop_ms`. Used as the Tier-C viseme fallback when phoneme
durations are unavailable, and as a standalone utility.
"""

from __future__ import annotations

import io

import numpy as np
import soundfile as sf

# RMS of ~0.1 in float PCM corresponds to loud speech; levels above it saturate to 1.0.
_LOUD_RMS = 0.1


def amplitude_envelope(audio_bytes: bytes, sample_rate: int, hop_ms: float = 16.0) -> list[tuple[float, float]]:
    """Decode WAV bytes and return (t_ms, mouth_open_0_to_1) per hop."""
    samples, _sr = sf.read(io.BytesIO(audio_bytes), dtype="float32")
    if samples.ndim > 1:
        samples = samples.mean(axis=1)
    hop = max(1, int(sample_rate * hop_ms / 1000.0))
    n_frames = len(samples) // hop
    out: list[tuple[float, float]] = []
    for i in range(n_frames):
        block = samples[i * hop : (i + 1) * hop]
        rms = float(np.sqrt(np.mean(block * block)))
        out.append((i * hop_ms, min(1.0, rms / _LOUD_RMS)))
    return out
