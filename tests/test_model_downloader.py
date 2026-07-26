from pathlib import Path

from par_tts.model_downloader import ModelDownloader


def test_timestamped_entry_present():
    md = ModelDownloader()
    assert "kokoro-v1.0-timestamped.onnx" in md.MODELS
    entry = md.MODELS["kokoro-v1.0-timestamped.onnx"]
    assert entry["url"].startswith("https://huggingface.co/")
    assert "Kokoro-82M-v1.0-ONNX-timestamped" in entry["url"]
    assert entry["url"].endswith("onnx/model.onnx")


def test_timestamped_path_under_data_dir():
    md = ModelDownloader()
    p = md.get_timestamped_model_path()
    assert p == md.data_dir / "kokoro-v1.0-timestamped.onnx"
    assert isinstance(p, Path)
