"""Offline diagnostics for PAR CLI TTS."""

from __future__ import annotations

import os
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path

from par_tts.model_downloader import ModelDownloader
from par_tts.providers import get_provider_plugins
from par_tts.voice_cache import VoiceCache


@dataclass(frozen=True)
class DiagnosticCheck:
    """One diagnostic check result."""

    name: str
    ok: bool
    detail: str


def _audio_player_candidates() -> list[str]:
    if sys.platform == "darwin":
        return ["afplay"]
    if sys.platform == "win32":
        return ["ffplay", "vlc", "mpg123", "powershell", "pwsh"]
    return ["paplay", "ffplay", "mpg123", "aplay"]


def check_audio_backends() -> list[DiagnosticCheck]:
    """Check whether a supported audio playback backend is present."""
    return [
        DiagnosticCheck(name=player, ok=shutil.which(player) is not None, detail=shutil.which(player) or "not found")
        for player in _audio_player_candidates()
    ]


def check_kokoro_models() -> list[DiagnosticCheck]:
    """Check Kokoro model file locations without downloading anything."""
    env_model_path = os.getenv("KOKORO_MODEL_PATH")
    env_voice_path = os.getenv("KOKORO_VOICE_PATH")
    if env_model_path or env_voice_path:
        model_path = Path(env_model_path or "")
        voice_path = Path(env_voice_path or "")
        return [
            DiagnosticCheck("KOKORO_MODEL_PATH", bool(env_model_path and model_path.exists()), str(model_path)),
            DiagnosticCheck("KOKORO_VOICE_PATH", bool(env_voice_path and voice_path.exists()), str(voice_path)),
        ]

    downloader = ModelDownloader()
    info = downloader.get_model_info()
    models = info["models"]
    return [
        DiagnosticCheck("model", bool(models["model"]["exists"]), models["model"]["path"]),
        DiagnosticCheck("voices", bool(models["voices"]["exists"]), models["voices"]["path"]),
    ]


def check_voice_cache() -> list[DiagnosticCheck]:
    """Check local ElevenLabs voice cache state without refreshing it."""
    cache = VoiceCache("par-tts-elevenlabs")
    cache_exists = cache.cache_file.exists()
    if not cache_exists:
        return [DiagnosticCheck("ElevenLabs voice cache", False, f"not found at {cache.cache_file}")]
    expired = cache.is_expired()
    return [
        DiagnosticCheck(
            "ElevenLabs voice cache",
            not expired,
            f"{'expired' if expired else 'fresh'} at {cache.cache_file}",
        )
    ]


def check_environment() -> list[DiagnosticCheck]:
    """Check provider API-key environment variables without revealing values."""
    checks: list[DiagnosticCheck] = []
    seen: set[str] = set()
    for plugin in get_provider_plugins().values():
        if not plugin.requires_api_key:
            continue
        for env_var in plugin.api_key_env_vars:
            if env_var in seen:
                continue
            seen.add(env_var)
            checks.append(
                DiagnosticCheck(
                    env_var,
                    bool(os.getenv(env_var)),
                    "set" if os.getenv(env_var) else "not set",
                )
            )
    return checks


def collect_diagnostics() -> dict[str, list[DiagnosticCheck]]:
    """Collect all offline diagnostics."""
    return {
        "Audio backends": check_audio_backends(),
        "Kokoro models": check_kokoro_models(),
        "ElevenLabs cache": check_voice_cache(),
        "Environment": check_environment(),
    }
