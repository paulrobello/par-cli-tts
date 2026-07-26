import numpy as np
from par_tts.providers.base import PhonemeSpan, VisemeSpan
from par_tts.alignment import pred_dur_to_timestamps, ipa_to_visemes, IPA_TO_VISEME, VISEMES


def test_viseme_set_is_nine_shapes():
    assert VISEMES == {"A", "B", "C", "D", "E", "F", "G", "H", "X"}


def test_pred_dur_to_timestamps_is_cumulative_and_monotonic():
    # 3 phonemes; pred_dur units are frames at frame_ms each.
    phonemes = ["h", "ə", "l"]
    pred_dur = np.array([4, 6, 5], dtype=np.int64)
    frame_ms = 12.5
    spans = pred_dur_to_timestamps(phonemes, pred_dur, frame_ms)
    assert len(spans) == 3
    starts = [s[1] for s in spans]
    ends = [s[2] for s in spans]
    assert starts == [0.0, 50.0, 125.0]          # 0, 4*12.5, (4+6)*12.5
    assert ends == [50.0, 125.0, 187.5]          # 4*12.5, 10*12.5, 15*12.5
    assert ends[-1] == sum(pred_dur) * frame_ms  # spans the whole audio


def test_ipa_to_visemes_maps_each_phoneme_and_drops_unknown():
    spans = [
        PhonemeSpan("m", 0.0, 40.0),
        PhonemeSpan("ɛ", 40.0, 90.0),   # EH -> C
        PhonemeSpan("ʔ", 90.0, 100.0),  # unknown -> X (rest)
    ]
    out = ipa_to_visemes(spans)
    assert [v.id for v in out] == ["A", "C", "X"]
    assert out[0].start_ms == 0.0 and out[0].end_ms == 40.0
    assert 0.0 <= out[0].intensity <= 1.0


def test_ipa_to_viseme_table_covers_common_english():
    # Representative coverage; each Rhubarb shape has at least one IPA entry.
    for shape in VISEMES - {"X"}:
        assert any(v == shape for v in IPA_TO_VISEME.values()), f"no IPA maps to {shape}"
