"""Built-in voice-pack metadata for common TTS use cases."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import resources
from typing import Any

import yaml

from par_tts.errors import ErrorType, TTSError


@dataclass(frozen=True)
class VoicePackRecommendation:
    """Provider/model/voice recommendation for a voice pack."""

    provider: str
    voice: str
    model: str | None = None
    notes: str | None = None


@dataclass(frozen=True)
class VoicePack:
    """Named collection of voice recommendations for a common use case."""

    name: str
    description: str
    recommendations: tuple[VoicePackRecommendation, ...]


def _config_error(message: str) -> TTSError:
    return TTSError(message, ErrorType.CONFIG_ERROR)


def _require_mapping(value: Any, context: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise _config_error(f"Malformed bundled voice-pack metadata: {context} must be a mapping")
    return value


def _require_string(value: Any, context: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise _config_error(f"Malformed bundled voice-pack metadata: {context} must be a non-empty string")
    return value


def _optional_string(value: Any, context: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise _config_error(f"Malformed bundled voice-pack metadata: {context} must be a string")
    return value


def load_voice_packs() -> dict[str, VoicePack]:
    """Load bundled voice-pack metadata.

    Returns:
        Mapping of voice-pack name to metadata.

    Raises:
        TTSError: If the bundled YAML is missing or malformed.
    """
    try:
        yaml_text = resources.files("par_tts").joinpath("data/voice_packs.yaml").read_text(encoding="utf-8")
        raw_data = yaml.safe_load(yaml_text)
    except TTSError:
        raise
    except Exception as exc:
        raise _config_error(f"Failed to load bundled voice-pack metadata: {exc}") from exc

    data = _require_mapping(raw_data, "top level")
    voice_packs: dict[str, VoicePack] = {}

    for pack_name, raw_pack in data.items():
        name = _require_string(pack_name, "voice-pack name")
        pack = _require_mapping(raw_pack, f"{name}")
        description = _require_string(pack.get("description"), f"{name}.description")
        raw_recommendations = pack.get("recommendations")
        if not isinstance(raw_recommendations, list) or not raw_recommendations:
            raise _config_error(
                f"Malformed bundled voice-pack metadata: {name}.recommendations must be a non-empty list"
            )

        recommendations: list[VoicePackRecommendation] = []
        for index, raw_recommendation in enumerate(raw_recommendations):
            context = f"{name}.recommendations[{index}]"
            recommendation = _require_mapping(raw_recommendation, context)
            recommendations.append(
                VoicePackRecommendation(
                    provider=_require_string(recommendation.get("provider"), f"{context}.provider"),
                    voice=_require_string(recommendation.get("voice"), f"{context}.voice"),
                    model=_optional_string(recommendation.get("model"), f"{context}.model"),
                    notes=_optional_string(recommendation.get("notes"), f"{context}.notes"),
                )
            )

        voice_packs[name] = VoicePack(
            name=name,
            description=description,
            recommendations=tuple(recommendations),
        )

    return voice_packs


def get_voice_pack(name: str) -> VoicePack:
    """Return a built-in voice pack by name.

    Raises:
        TTSError: If *name* is unknown, with available names in the message.
    """
    voice_packs = load_voice_packs()
    try:
        return voice_packs[name]
    except KeyError as exc:
        available = ", ".join(sorted(voice_packs)) or "none"
        raise TTSError(f"Unknown voice pack '{name}'. Available voice packs: {available}", ErrorType.INVALID_INPUT) from exc
