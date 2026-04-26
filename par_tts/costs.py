"""Static synthesis cost estimation helpers."""

from __future__ import annotations

from dataclasses import dataclass

from par_tts.defaults import DEFAULT_MODELS

# Approximate per-million-character rates for quick estimates. Cloud provider
# billing changes over time, so treat these as planning numbers only.
COST_PER_MILLION_CHARS: dict[str, dict[str, float]] = {
    "openai": {"default": 15.0, "tts-1": 15.0, "tts-1-hd": 30.0, "gpt-4o-mini-tts": 15.0},
    "elevenlabs": {"default": 30.0},
    "deepgram": {"default": 30.0},
    "gemini": {"default": 0.50},
    "kokoro-onnx": {"default": 0.0, "kokoro-v1.0": 0.0},
}


@dataclass(frozen=True)
class CostEstimate:
    """Static, approximate synthesis cost estimate."""

    provider: str
    model: str
    characters: int
    cost_usd: float | None
    rate_per_million: float | None


def estimate_synthesis_cost(provider: str, model: str | None, text: str) -> CostEstimate:
    """Estimate synthesis cost from static provider/model pricing."""
    resolved_model = model or DEFAULT_MODELS.get(provider, "default")
    provider_rates = COST_PER_MILLION_CHARS.get(provider, {})
    rate = provider_rates.get(resolved_model, provider_rates.get("default"))
    characters = len(text)
    cost = None if rate is None else (characters / 1_000_000) * rate
    return CostEstimate(
        provider=provider,
        model=resolved_model,
        characters=characters,
        cost_usd=cost,
        rate_per_million=rate,
    )
