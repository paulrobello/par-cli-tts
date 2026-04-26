"""Workflow automation helpers for batch, templates, watch mode, and captions."""

from __future__ import annotations

import csv
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class BatchRecord:
    """One row from a batch synthesis input file."""

    text: str
    output: Path | None = None
    metadata: dict[str, Any] | None = None


@dataclass(frozen=True)
class TimestampEntry:
    """Rough timing metadata for one spoken text segment."""

    index: int
    start_seconds: float
    end_seconds: float
    text: str


@dataclass(frozen=True)
class NotificationDefaults:
    """Resolved low-latency defaults for short notification playback."""

    model: str | None
    speed: float
    post_process_preset: str
    trim_silence: bool
    play_audio: bool

    @classmethod
    def from_options(cls, *, provider: str, model: str | None, play_audio: bool) -> NotificationDefaults:
        """Build notification defaults without clobbering explicit model/play choices."""
        low_latency_model = "tts-1" if provider == "openai" and model is None else model
        return cls(
            model=low_latency_model,
            speed=1.15,
            post_process_preset="notification",
            trim_silence=True,
            play_audio=play_audio,
        )


_BATCH_TEXT_FIELDS = ("text", "message", "script", "content")
_BATCH_OUTPUT_FIELDS = ("output", "output_path", "filename", "file")
_WATCH_SUFFIXES = {".md", ".markdown", ".txt", ".rst"}
_MIN_SEGMENT_SECONDS = 1.0


def parse_batch_records(
    path: Path, *, text_field: str | None = None, output_field: str | None = None
) -> list[BatchRecord]:
    """Parse CSV or JSONL batch records.

    The first available text field among ``text``, ``message``, ``script``, and
    ``content`` is used by default. Output path is optional and may be supplied
    through ``output``, ``output_path``, ``filename``, or ``file``.
    """
    batch_path = Path(path).expanduser()
    suffix = batch_path.suffix.lower()
    if suffix == ".csv":
        return _parse_csv_batch(batch_path, text_field=text_field, output_field=output_field)
    if suffix in {".jsonl", ".ndjson"}:
        return _parse_jsonl_batch(batch_path, text_field=text_field, output_field=output_field)
    raise ValueError("Batch input must be a .csv, .jsonl, or .ndjson file")


def _parse_csv_batch(path: Path, *, text_field: str | None, output_field: str | None) -> list[BatchRecord]:
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return [
            _record_from_mapping(row, index=index, text_field=text_field, output_field=output_field)
            for index, row in enumerate(reader, start=1)
        ]


def _parse_jsonl_batch(path: Path, *, text_field: str | None, output_field: str | None) -> list[BatchRecord]:
    records: list[BatchRecord] = []
    with open(path, encoding="utf-8") as f:
        for index, line in enumerate(f, start=1):
            stripped = line.strip()
            if not stripped:
                continue
            data = json.loads(stripped)
            if not isinstance(data, dict):
                raise ValueError(f"Batch line {index} must be a JSON object")
            records.append(_record_from_mapping(data, index=index, text_field=text_field, output_field=output_field))
    return records


def _record_from_mapping(
    data: dict[str, Any], *, index: int, text_field: str | None, output_field: str | None
) -> BatchRecord:
    selected_text_field = text_field or _first_present(data, _BATCH_TEXT_FIELDS)
    if not selected_text_field or selected_text_field not in data or str(data[selected_text_field]).strip() == "":
        raise ValueError(f"Batch row {index} is missing a text field")

    selected_output_field = output_field or _first_present(data, _BATCH_OUTPUT_FIELDS)
    output_value = data.get(selected_output_field) if selected_output_field else None
    output = Path(str(output_value)) if output_value not in (None, "") else None
    excluded = {selected_text_field}
    if selected_output_field:
        excluded.add(selected_output_field)
    metadata = {key: value for key, value in data.items() if key not in excluded and value not in (None, "")}
    return BatchRecord(text=str(data[selected_text_field]).strip(), output=output, metadata=metadata)


def _first_present(data: dict[str, Any], candidates: tuple[str, ...]) -> str | None:
    lowered = {key.lower(): key for key in data}
    for candidate in candidates:
        if candidate in lowered:
            return lowered[candidate]
    return None


def parse_template_vars(values: list[str] | None) -> dict[str, str]:
    """Parse repeated KEY=VALUE template variable options."""
    variables: dict[str, str] = {}
    for value in values or []:
        if "=" not in value:
            raise ValueError(f"Invalid template variable '{value}'. Expected KEY=VALUE")
        key, replacement = value.split("=", 1)
        key = key.strip()
        if not key:
            raise ValueError(f"Invalid template variable '{value}'. Expected KEY=VALUE")
        variables[key] = replacement
    return variables


def render_template(template: str, variables: dict[str, str]) -> str:
    """Render a tiny safe template syntax for repeated scripts.

    Supports both ``{{ name }}`` and Python-format-style ``{name}`` placeholders.
    Unknown variables are left untouched so normal braces in scripts are not
    destructive.
    """
    rendered = re.sub(
        r"\{\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}\}",
        lambda match: variables.get(match.group(1), match.group(0)),
        template,
    )
    return re.sub(
        r"(?<!\{)\{\s*([A-Za-z_][A-Za-z0-9_]*)\s*\}(?!\})",
        lambda match: variables.get(match.group(1), match.group(0)),
        rendered,
    )


def split_caption_segments(text: str) -> list[str]:
    """Split text into sentence-sized caption segments."""
    return [part.strip() for part in re.split(r"(?<=[.!?])\s+", text.strip()) if part.strip()]


def build_timestamp_entries(segments: list[str], *, words_per_minute: int = 160) -> list[TimestampEntry]:
    """Build rough sequential timestamp entries for text segments."""
    entries: list[TimestampEntry] = []
    cursor = 0.0
    words_per_second = max(words_per_minute, 1) / 60
    for index, segment in enumerate(segments, start=1):
        word_count = max(len(segment.split()), 1)
        duration = max(word_count / words_per_second, _MIN_SEGMENT_SECONDS)
        end = cursor + duration
        entries.append(
            TimestampEntry(
                index=index,
                start_seconds=round(cursor, 3),
                end_seconds=round(end, 3),
                text=segment,
            )
        )
        cursor = end
    return entries


def format_srt_entries(entries: list[TimestampEntry]) -> str:
    """Format timestamp entries as SRT captions."""
    blocks = [
        f"{entry.index}\n{_format_srt_time(entry.start_seconds)} --> {_format_srt_time(entry.end_seconds)}\n{entry.text}"
        for entry in entries
    ]
    return "\n\n".join(blocks) + ("\n" if blocks else "")


def write_timestamp_export(path: Path, entries: list[TimestampEntry], *, output_format: str) -> None:
    """Write timestamp entries as JSON or SRT."""
    export_path = Path(path).expanduser()
    export_path.parent.mkdir(parents=True, exist_ok=True)
    if output_format == "json":
        export_path.write_text(json.dumps([asdict(entry) for entry in entries], indent=2) + "\n", encoding="utf-8")
        return
    if output_format == "srt":
        export_path.write_text(format_srt_entries(entries), encoding="utf-8")
        return
    raise ValueError("Timestamp format must be 'json' or 'srt'")


def discover_watch_inputs(path: Path) -> list[Path]:
    """Return text-like files watched by docs-to-audio mode."""
    watch_path = Path(path).expanduser()
    if watch_path.is_file():
        return [watch_path]
    if not watch_path.is_dir():
        raise ValueError(f"Watch path does not exist: {watch_path}")
    return sorted(item for item in watch_path.rglob("*") if item.is_file() and item.suffix.lower() in _WATCH_SUFFIXES)


def watch_snapshot(path: Path) -> dict[Path, float]:
    """Return modification times for current watch inputs."""
    return {item: item.stat().st_mtime for item in discover_watch_inputs(path)}


def changed_watch_inputs(previous: dict[Path, float], current: dict[Path, float]) -> list[Path]:
    """Return files that are new or changed between watch snapshots."""
    return sorted(path for path, mtime in current.items() if previous.get(path) != mtime)


def output_path_for_record(record: BatchRecord, *, output_dir: Path, index: int, suffix: str = ".mp3") -> Path:
    """Resolve a safe output path for a batch record."""
    if record.output:
        candidate = record.output
        return candidate if candidate.is_absolute() else output_dir / candidate
    return output_dir / f"item_{index:04d}{suffix}"


def _format_srt_time(seconds: float) -> str:
    milliseconds = int(round(seconds * 1000))
    hours, remainder = divmod(milliseconds, 3_600_000)
    minutes, remainder = divmod(remainder, 60_000)
    secs, millis = divmod(remainder, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"
