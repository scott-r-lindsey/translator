from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from typing import Protocol


class AudioStatus(StrEnum):
    READY = "Ready"
    CAPTURE_UNAVAILABLE = "Audio capture unavailable"
    LISTENING = "Listening..."
    SILENCE = "Silence"
    AUDIO_DETECTED = "Audio detected"
    SPEECH_DETECTED = "Speech detected"
    TRANSCRIBING = "Transcribing"
    TRANSCRIPTION_UNAVAILABLE = "Transcription unavailable"


class DisplayEventKind(StrEnum):
    STATUS = "status"
    CAPTION = "caption"


@dataclass(frozen=True)
class DisplayEvent:
    kind: DisplayEventKind
    text: str = ""
    source_text: str = ""
    translated_text: str = ""
    detected_language: str | None = None


class SegmentEndReason(StrEnum):
    SILENCE = "silence"
    MAX_DURATION = "max-duration"


StatusCallback = Callable[[DisplayEvent], None]


class AudioActivityMonitor(Protocol):
    def prepare(self, on_status: StatusCallback) -> None:
        ...

    def start(self, on_status: StatusCallback) -> None:
        ...

    def stop(self) -> None:
        ...

    def set_source_language(self, language: str | None) -> None:
        ...


class VoiceActivityDetector(Protocol):
    def is_speech(self, chunk: bytes) -> bool:
        ...


def status_event(text: str) -> DisplayEvent:
    return DisplayEvent(kind=DisplayEventKind.STATUS, text=text)


def caption_event(
    source_text: str,
    translated_text: str,
    detected_language: str | None = None,
) -> DisplayEvent:
    return DisplayEvent(
        kind=DisplayEventKind.CAPTION,
        source_text=source_text,
        translated_text=translated_text,
        detected_language=detected_language,
    )
