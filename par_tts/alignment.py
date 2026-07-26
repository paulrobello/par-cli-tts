"""Pure lip-sync conversions for Kokoro timestamped output.

`pred_dur` is the per-phoneme duration tensor the timestamped Kokoro model emits
alongside audio. Each unit is one frame of `frame_ms` milliseconds (the spike in
Task 4 pins the real value; tests inject a known `frame_ms`). The IPA→viseme
table is transcribed from Rhubarb's `src/animation/animationRules.cpp` (phoneme
→ primary shape), expressed in IPA since Kokoro's G2P emits IPA.
"""

from __future__ import annotations

import numpy as np

from .providers.base import PhonemeSpan, VisemeSpan

VISEMES: set[str] = {"A", "B", "C", "D", "E", "F", "G", "H", "X"}

# IPA symbol -> Rhubarb viseme (primary shape). Source: Rhubarb animationRules.cpp,
# ARPABET→shape, converted to the IPA Kokoro emits. Unknown -> "X" (rest).
IPA_TO_VISEME: dict[str, str] = {
    # Vowels
    "ɑ": "D",
    "ɑː": "D",
    "æ": "C",
    "ɛ": "C",
    "e": "C",
    "ɪ": "B",
    "i": "B",
    "iː": "B",
    "ɔ": "E",
    "o": "E",
    "ʊ": "F",
    "u": "F",
    "uː": "F",
    "ʌ": "C",
    "ə": "B",
    "ɚ": "E",
    "aɪ": "C",
    "aʊ": "C",
    "eɪ": "C",
    "oʊ": "E",
    "ɔɪ": "E",
    # Consonants
    "p": "A",
    "b": "A",
    "m": "A",
    "f": "G",
    "v": "G",
    "θ": "B",
    "ð": "B",
    "s": "B",
    "z": "B",
    "ʃ": "B",
    "ʒ": "B",
    "t": "B",
    "d": "B",
    "n": "B",
    "l": "H",
    "r": "B",
    "k": "B",
    "g": "B",
    "ŋ": "B",
    "tʃ": "B",
    "dʒ": "B",
    "j": "B",
    "w": "F",
    "h": "X",
}


def pred_dur_to_timestamps(
    phonemes: list[str], pred_dur: np.ndarray, frame_ms: float
) -> list[tuple[str, float, float]]:
    """Convert per-phoneme frame counts to (ipa, start_ms, end_ms) spans."""
    starts = np.concatenate([[0.0], np.cumsum(pred_dur, dtype=np.float64)[:-1]]) * frame_ms
    ends = np.cumsum(pred_dur, dtype=np.float64) * frame_ms
    return [(ipa, float(starts[i]), float(ends[i])) for i, ipa in enumerate(phonemes) if i < len(pred_dur)]


def ipa_to_visemes(spans: list[PhonemeSpan]) -> list[VisemeSpan]:
    """Map phoneme spans to Rhubarb visemes; unknown phonemes become X (rest)."""
    out: list[VisemeSpan] = []
    for s in spans:
        vis_id = IPA_TO_VISEME.get(s.ipa, "X")
        # Vowels get full intensity; consonants/rest are softer (affects jaw drop).
        intensity = 1.0 if vis_id in {"B", "C", "D", "E", "F"} else 0.6
        out.append(VisemeSpan(id=vis_id, start_ms=s.start_ms, end_ms=s.end_ms, intensity=intensity))
    return out
