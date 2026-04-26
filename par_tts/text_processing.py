"""Provider-neutral text preprocessing helpers for PAR TTS."""

from __future__ import annotations

import re
from dataclasses import dataclass, replace


@dataclass(frozen=True)
class TextSegment:
    """A text span plus optional generation metadata."""

    text: str
    voice: str | None = None
    lang: str | None = None
    speed: float | None = None
    pause_after_ms: int = 0


@dataclass(frozen=True)
class TextProcessingOptions:
    """Options for provider-neutral text preprocessing."""

    pronunciations: dict[str, str] | None = None
    markup: bool = False
    voice_sections: bool = False
    chunk: bool = False
    max_chars: int = 1200
    auto_lang: bool = False

    def __post_init__(self) -> None:
        if self.max_chars <= 0:
            raise ValueError("max_chars must be greater than 0")


def apply_pronunciations(text: str, pronunciations: dict[str, str] | None) -> str:
    """Apply whole-word pronunciation replacements case-insensitively."""
    if not pronunciations:
        return text

    result = text
    for source, replacement in sorted(pronunciations.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = re.compile(rf"\b{re.escape(source)}\b", re.IGNORECASE)
        result = pattern.sub(replacement, result)
    return result


def split_text_chunks(text: str, max_chars: int = 1200) -> list[str]:
    """Split text into chunks, preferring paragraph and sentence boundaries."""
    cleaned = text.strip()
    if not cleaned:
        return []
    if max_chars <= 0 or len(cleaned) <= max_chars:
        return [cleaned]

    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", cleaned) if part.strip()]
    chunks: list[str] = []
    current = ""

    for paragraph in paragraphs:
        sentences = _split_sentences(paragraph)
        for sentence in sentences:
            if len(sentence) > max_chars:
                if current:
                    chunks.append(current)
                    current = ""
                chunks.extend(_hard_wrap(sentence, max_chars))
                continue

            candidate = f"{current} {sentence}".strip() if current else sentence
            if len(candidate) <= max_chars:
                current = candidate
            else:
                if current:
                    chunks.append(current)
                current = sentence

        if current and len(current) >= max_chars:
            chunks.append(current)
            current = ""

    if current:
        chunks.append(current)
    return chunks


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip())
    return [part.strip() for part in parts if part.strip()]


def _hard_wrap(text: str, max_chars: int) -> list[str]:
    words = text.split()
    chunks: list[str] = []
    current = ""
    for word in words:
        candidate = f"{current} {word}".strip() if current else word
        if len(candidate) <= max_chars:
            current = candidate
        else:
            if current:
                chunks.append(current)
            current = word
    if current:
        chunks.append(current)
    return chunks


def parse_lightweight_markup(text: str) -> list[TextSegment]:
    """Parse a deliberately small SSML-like subset into text segments.

    Supported forms:
    - ``<break time="500ms"/>`` or ``[pause=500ms]`` pauses after prior text.
    - ``<prosody rate="slow|fast|1.2">text</prosody>`` speed metadata.
    - ``<emphasis>text</emphasis>`` strips the tag and keeps the text.
    """
    normalized = re.sub(r"\[pause=(\d+)ms\]", r'<break time="\1ms"/>', text)
    tokens = re.split(r"(<break\s+time=['\"]?\d+ms['\"]?\s*/>)", normalized, flags=re.IGNORECASE)
    segments: list[TextSegment] = []

    for token in tokens:
        if not token:
            continue
        pause_match = re.fullmatch(r"<break\s+time=['\"]?(\d+)ms['\"]?\s*/>", token.strip(), flags=re.IGNORECASE)
        if pause_match:
            pause_ms = int(pause_match.group(1))
            if segments:
                segments[-1] = replace(segments[-1], pause_after_ms=pause_ms)
            continue
        segments.extend(_parse_prosody_segments(token))

    return _merge_adjacent_segments(segments)


def _parse_prosody_segments(text: str) -> list[TextSegment]:
    pattern = re.compile(
        r"<prosody\s+rate=['\"]?([^'\">]+)['\"]?>(.*?)</prosody>",
        flags=re.IGNORECASE | re.DOTALL,
    )
    segments: list[TextSegment] = []
    position = 0
    for match in pattern.finditer(text):
        before = _strip_markup(text[position : match.start()]).strip()
        body = _strip_markup(match.group(2)).strip()
        rate = _parse_rate(match.group(1))
        if before and body:
            segments.append(TextSegment(text=f"{before} {body}".strip(), speed=rate))
        elif before:
            segments.append(TextSegment(text=before))
        elif body:
            segments.append(TextSegment(text=body, speed=rate))
        position = match.end()

    remainder = _strip_markup(text[position:]).strip()
    if remainder:
        segments.append(TextSegment(text=remainder))
    return segments


def _strip_markup(text: str) -> str:
    text = re.sub(r"</?emphasis>", "", text, flags=re.IGNORECASE)
    return re.sub(r"\s+", " ", text).strip()


def _parse_rate(rate: str) -> float:
    lowered = rate.lower().strip()
    if lowered == "slow":
        return 0.85
    if lowered == "fast":
        return 1.15
    try:
        return float(lowered)
    except ValueError:
        return 1.0


def _merge_adjacent_segments(segments: list[TextSegment]) -> list[TextSegment]:
    merged: list[TextSegment] = []
    for segment in segments:
        if not segment.text:
            continue
        if merged and re.fullmatch(r"[.!?,;:]+", segment.text):
            merged[-1] = replace(merged[-1], text=f"{merged[-1].text}{segment.text}")
        elif (
            merged
            and merged[-1].voice == segment.voice
            and merged[-1].lang == segment.lang
            and merged[-1].speed == segment.speed
            and merged[-1].pause_after_ms == 0
            and segment.pause_after_ms == 0
        ):
            merged[-1] = replace(merged[-1], text=f"{merged[-1].text} {segment.text}".strip())
        else:
            merged.append(segment)
    return merged


def parse_voice_sections(text: str) -> list[TextSegment]:
    """Parse paragraph prefixes like ``voice=nova; speed=1.1 | Hello``."""
    sections = [part.strip() for part in re.split(r"\n\s*\n", text.strip()) if part.strip()]
    segments: list[TextSegment] = []
    for section in sections:
        if "|" not in section:
            segments.append(TextSegment(text=section))
            continue
        metadata_text, body = section.split("|", 1)
        metadata = _parse_section_metadata(metadata_text)
        segments.append(
            TextSegment(
                text=body.strip(),
                voice=metadata.get("voice"),
                lang=metadata.get("lang"),
                speed=float(metadata["speed"]) if "speed" in metadata else None,
            )
        )
    return segments


def _parse_section_metadata(text: str) -> dict[str, str]:
    metadata: dict[str, str] = {}
    for item in re.split(r"[;,]", text):
        if "=" not in item:
            continue
        key, value = item.split("=", 1)
        key = key.strip().lower()
        if key in {"voice", "lang", "speed"}:
            metadata[key] = value.strip()
    return metadata


def auto_detect_lang(text: str) -> str:
    """Detect obvious language/script with no external dependency."""
    if re.search(r"[\u3040-\u30ff\u3400-\u9fff]", text):
        return "ja"
    if re.search(r"[\u0400-\u04ff]", text):
        return "ru"
    if re.search(r"[\u0600-\u06ff]", text):
        return "ar"
    if re.search(r"[\u0590-\u05ff]", text):
        return "he"
    return "en-us"


def build_text_segments(
    text: str,
    *,
    options: TextProcessingOptions | None = None,
    pronunciations: dict[str, str] | None = None,
    markup: bool = False,
    voice_sections: bool = False,
    chunk: bool = False,
    max_chars: int = 1200,
    auto_lang: bool = False,
) -> list[TextSegment]:
    """Build generation segments from raw input and pipeline options."""
    active_options = options or TextProcessingOptions(
        pronunciations=pronunciations,
        markup=markup,
        voice_sections=voice_sections,
        chunk=chunk,
        max_chars=max_chars,
        auto_lang=auto_lang,
    )
    rewritten = apply_pronunciations(text, active_options.pronunciations)
    if active_options.voice_sections:
        segments = parse_voice_sections(rewritten)
    elif active_options.markup:
        segments = parse_lightweight_markup(rewritten)
    else:
        segments = [TextSegment(text=rewritten.strip())]

    expanded: list[TextSegment] = []
    for segment in segments:
        chunks = (
            split_text_chunks(segment.text, max_chars=active_options.max_chars)
            if active_options.chunk
            else [segment.text.strip()]
        )
        for chunk_text in chunks:
            if not chunk_text:
                continue
            lang = segment.lang or (auto_detect_lang(chunk_text) if active_options.auto_lang else None)
            expanded.append(
                TextSegment(
                    text=chunk_text,
                    voice=segment.voice,
                    lang=lang,
                    speed=segment.speed,
                    pause_after_ms=segment.pause_after_ms,
                )
            )
    return expanded
