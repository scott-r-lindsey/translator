from dataclasses import dataclass

from translator.languages import source_language_label


@dataclass(frozen=True)
class TranscriptEntry:
    timestamp_seconds: float
    source_text: str
    translated_text: str
    detected_language: str | None


def render_transcript_entry(entry: TranscriptEntry) -> str:
    timestamp = format_timestamp(entry.timestamp_seconds)
    language = source_language_label(entry.detected_language)
    lines = [f"[{timestamp}] {language}"]
    if entry.source_text:
        lines.append(entry.source_text)
    if entry.translated_text:
        lines.append(entry.translated_text)

    return "\n".join(lines)


def format_timestamp(seconds: float) -> str:
    total_seconds = max(int(seconds), 0)
    minutes, seconds = divmod(total_seconds, 60)
    hours, minutes = divmod(minutes, 60)
    if hours:
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    return f"{minutes:02d}:{seconds:02d}"

