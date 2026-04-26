"""Tests for workflow automation helpers."""

from pathlib import Path

from par_tts.workflow import (
    BatchRecord,
    NotificationDefaults,
    build_timestamp_entries,
    discover_watch_inputs,
    format_srt_entries,
    parse_batch_records,
    parse_template_vars,
    render_template,
)


def test_parse_batch_records_reads_csv_text_and_metadata(tmp_path: Path):
    """CSV batch files should produce text plus per-row output and metadata."""
    batch_file = tmp_path / "batch.csv"
    batch_file.write_text("id,text,voice,output\nintro,Hello there,nova,intro.mp3\n", encoding="utf-8")

    records = parse_batch_records(batch_file)

    assert records == [
        BatchRecord(
            text="Hello there",
            output=Path("intro.mp3"),
            metadata={"id": "intro", "voice": "nova"},
        )
    ]


def test_parse_batch_records_reads_jsonl_text_and_metadata(tmp_path: Path):
    """JSONL batch files should support text, output, and arbitrary metadata fields."""
    batch_file = tmp_path / "batch.jsonl"
    batch_file.write_text(
        '{"text":"Hello JSON","output":"hello.mp3","voice":"onyx","speed":1.2}\n',
        encoding="utf-8",
    )

    records = parse_batch_records(batch_file)

    assert records == [
        BatchRecord(
            text="Hello JSON",
            output=Path("hello.mp3"),
            metadata={"voice": "onyx", "speed": 1.2},
        )
    ]


def test_render_template_replaces_double_brace_and_plain_brace_variables():
    """Template variables should support common {{name}} and {name} forms."""
    variables = parse_template_vars(["name=Paul", "date=2026-04-26"])

    assert render_template("Hello {{ name }} on {date}.", variables) == "Hello Paul on 2026-04-26."


def test_render_template_preserves_non_variable_braces():
    """Template rendering should not break scripts that contain JSON or unknown placeholders."""
    template = 'Payload: {"name": "{name}", "unknown": "{missing}"}'

    assert render_template(template, {"name": "Paul"}) == 'Payload: {"name": "Paul", "unknown": "{missing}"}'


def test_build_timestamp_entries_and_srt_output_are_deterministic():
    """Timestamp export should create rough sequential sentence timings."""
    entries = build_timestamp_entries(["Hello world.", "Second line."], words_per_minute=120)

    assert [entry.index for entry in entries] == [1, 2]
    assert entries[0].start_seconds == 0.0
    assert entries[0].end_seconds == 1.0
    assert entries[1].start_seconds == 1.0
    assert entries[1].text == "Second line."
    assert "00:00:00,000 --> 00:00:01,000" in format_srt_entries(entries)
    assert "Second line." in format_srt_entries(entries)


def test_discover_watch_inputs_returns_text_files_for_file_or_folder(tmp_path: Path):
    """Watch mode should accept a file or discover common document files in a folder."""
    docs = tmp_path / "docs"
    docs.mkdir()
    md = docs / "guide.md"
    txt = docs / "notes.txt"
    ignored = docs / "image.png"
    md.write_text("# Guide", encoding="utf-8")
    txt.write_text("Notes", encoding="utf-8")
    ignored.write_bytes(b"png")

    assert discover_watch_inputs(md) == [md]
    assert discover_watch_inputs(docs) == [md, txt]


def test_notification_defaults_optimize_for_short_low_latency_messages():
    """Notification mode should set low-latency defaults without overriding explicit values."""
    defaults = NotificationDefaults.from_options(provider="openai", model=None, play_audio=True)

    assert defaults.model == "tts-1"
    assert defaults.speed == 1.15
    assert defaults.post_process_preset == "notification"
    assert defaults.trim_silence is True
    assert defaults.play_audio is True

    explicit = NotificationDefaults.from_options(provider="openai", model="gpt-4o-mini-tts", play_audio=False)

    assert explicit.model == "gpt-4o-mini-tts"
    assert explicit.play_audio is False
