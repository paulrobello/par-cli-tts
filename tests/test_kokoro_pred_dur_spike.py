# tests/test_kokoro_pred_dur_spike.py
"""Validation spike: confirm pred_dur is extractable from the timestamped model.
Skipped unless the model is present. Run with: uv run pytest tests/test_kokoro_pred_dur_spike.py -v -s
"""
import numpy as np
import onnxruntime as rt
import pytest

from par_tts.model_downloader import ModelDownloader
from kokoro_onnx import Kokoro


def test_pred_dur_extractable_and_sane():
    md = ModelDownloader()
    path = md.get_timestamped_model_path()
    if not path.exists():
        pytest.skip(f"timestamped model not present at {path}; download it first")
    # Reuse the standard-model Kokoro for its tokenizer + voices, but swap the session
    # for the timestamped one (from_session reuses tokenizer/voices).
    std_model, voices = md.get_model_paths()
    if not std_model.exists():
        pytest.skip("standard kokoro model not present")
    base = Kokoro(str(std_model), str(voices))
    sess = rt.InferenceSession(str(path), providers=["CPUExecutionProvider"])
    base.sess = sess  # run the timestamped session through the same Kokoro machinery

    outputs = sess.get_outputs()
    print("output names:", [o.name for o in outputs])
    assert len(outputs) >= 2, "timestamped model must expose a second (pred_dur) output"

    voice = base.get_voice_style("af_heart")
    phonemes = base.tokenizer.phonemize("hello world", "en-us")
    tokens = np.array(base.tokenizer.tokenize(phonemes), dtype=np.int64)
    inputs = {
        "input_ids": [[0, *tokens, 0]],
        "style": np.array(voice[len(tokens)], dtype=np.float32),
        "speed": np.array([1.0], dtype=np.float32),
    }
    out = sess.run(None, inputs)
    audio, pred_dur = out[0], out[1]
    # NOTE: audio has shape (1, N); len() returns the batch axis (=1), so use .size for sample count.
    audio_ms = np.array(audio).size / 24000 * 1000
    # frame_ms is the unknown this spike pins: audio_ms ≈ sum(pred_dur) * frame_ms.
    # Brief hypothesised 8-16ms (Rhubarb-default-like); empirical result from this run
    # was ~25.4ms (see task-4-report.md) — Kokoro's duration-unit is coarser than expected,
    # so the assertion accepts the empirically observed range. Task 5 must use the printed value.
    frame_ms = audio_ms / float(np.array(pred_dur).flatten().sum())
    print(f"audio_ms={audio_ms:.1f}  sum(pred_dur)={float(np.array(pred_dur).sum())}  frame_ms={frame_ms:.3f}")
    assert 20.0 < frame_ms < 35.0, f"frame_ms {frame_ms} outside empirically observed range"
