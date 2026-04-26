from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from par_tts import voice_packs
from par_tts.errors import ErrorType, TTSError
from par_tts.voice_packs import VoicePack, load_voice_packs


def test_load_voice_packs_returns_required_bundled_packs() -> None:
    packs = load_voice_packs()

    assert {"alerts", "assistant", "narration", "storytelling"}.issubset(packs)
    for pack_name in ("alerts", "assistant", "narration", "storytelling"):
        pack = packs[pack_name]
        assert isinstance(pack, VoicePack)
        assert pack.name == pack_name
        assert pack.description
        assert pack.recommendations


def test_get_voice_pack_returns_assistant_pack() -> None:
    pack = voice_packs.get_voice_pack("assistant")

    assert isinstance(pack, VoicePack)
    assert pack.name == "assistant"


def test_get_voice_pack_unknown_name_reports_available_names() -> None:
    with pytest.raises(TTSError) as exc_info:
        voice_packs.get_voice_pack("does-not-exist")

    assert "Unknown voice pack" in str(exc_info.value)
    assert "alerts" in str(exc_info.value)
    assert "assistant" in str(exc_info.value)
    assert "narration" in str(exc_info.value)
    assert "storytelling" in str(exc_info.value)


def test_load_voice_packs_malformed_bundled_yaml_raises_config_error(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    data_dir = tmp_path / "data"
    data_dir.mkdir()
    (data_dir / "voice_packs.yaml").write_text(
        "assistant:\n  description: Friendly assistant voices\n", encoding="utf-8"
    )

    def fake_files(package: str) -> Any:
        assert package == "par_tts"
        return tmp_path

    monkeypatch.setattr(voice_packs.resources, "files", fake_files)

    with pytest.raises(TTSError) as exc_info:
        load_voice_packs()

    assert exc_info.value.error_type is ErrorType.CONFIG_ERROR
