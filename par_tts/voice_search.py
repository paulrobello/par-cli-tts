"""Provider-neutral voice search helpers."""

from __future__ import annotations

from collections.abc import Iterable
from typing import Any


def search_voices(voices: Iterable[Any], query: str) -> list[Any]:
    """Search provider voices by id, name, labels, and category."""
    scored = [(_fuzzy_score(query, _voice_search_text(voice)), voice) for voice in voices]
    return [voice for score, voice in sorted(scored, key=lambda item: item[0], reverse=True) if score > 0]


def _voice_search_text(voice: Any) -> str:
    labels = " ".join(voice.labels or [])
    return f"{voice.id} {voice.name} {labels} {voice.category or ''}".lower()


def _fuzzy_score(query: str, candidate: str) -> int:
    """Return a simple fuzzy score; lower means no match."""
    query = query.lower().strip()
    if not query:
        return 0
    if query in candidate:
        return 100 + len(query)

    position = -1
    score = 0
    for char in query:
        next_position = candidate.find(char, position + 1)
        if next_position == -1:
            return 0
        score += 5 if next_position == position + 1 else 1
        position = next_position
    return score
