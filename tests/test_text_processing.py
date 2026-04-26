"""Tests for provider-neutral text processing pipeline helpers."""

from par_tts.text_processing import (
    TextSegment,
    apply_pronunciations,
    auto_detect_lang,
    parse_lightweight_markup,
    parse_voice_sections,
    split_text_chunks,
)


def test_apply_pronunciations_replaces_words_case_insensitively():
    """Pronunciation dictionary should replace whole words only."""
    result = apply_pronunciations("NASA and api calls, not capillary", {"NASA": "N A S A", "API": "A P I"})

    assert result == "N A S A and A P I calls, not capillary"


def test_split_text_chunks_prefers_sentence_boundaries():
    """Long text should split on sentence boundaries where possible."""
    chunks = split_text_chunks("One sentence. Two sentence. Three sentence.", max_chars=24)

    assert chunks == ["One sentence.", "Two sentence.", "Three sentence."]


def test_parse_lightweight_markup_extracts_pause_and_prosody():
    """Lightweight markup should create segment metadata without leaving tags in text."""
    segments = parse_lightweight_markup('Hello <break time="500ms"/> <prosody rate="slow">carefully</prosody>.')

    assert segments == [
        TextSegment(text="Hello", pause_after_ms=500),
        TextSegment(text="carefully.", speed=0.85),
    ]


def test_parse_voice_sections_reads_per_paragraph_metadata():
    """Voice section prefixes should apply metadata to paragraph text."""
    segments = parse_voice_sections("voice=nova; speed=1.1 | Hello\n\nvoice=onyx; lang=en-us | World")

    assert segments == [
        TextSegment(text="Hello", voice="nova", speed=1.1),
        TextSegment(text="World", voice="onyx", lang="en-us"),
    ]


def test_auto_detect_lang_detects_obvious_scripts():
    """Language detection should provide useful no-dependency script heuristics."""
    assert auto_detect_lang("これはテストです") == "ja"
    assert auto_detect_lang("Привет мир") == "ru"
    assert auto_detect_lang("Hello world") == "en-us"
