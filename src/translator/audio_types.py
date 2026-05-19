from collections.abc import Callable
from enum import StrEnum
from typing import Protocol


class AudioStatus(StrEnum):
    CAPTURE_UNAVAILABLE = "Audio capture unavailable"
    LISTENING = "Listening..."
    SILENCE = "Silence"
    AUDIO_DETECTED = "Audio detected"
    SPEECH_DETECTED = "Speech detected"
    TRANSCRIBING = "Transcribing"
    TRANSCRIPTION_UNAVAILABLE = "Transcription unavailable"


class SegmentEndReason(StrEnum):
    SILENCE = "silence"
    MAX_DURATION = "max-duration"


StatusCallback = Callable[[str], None]


class AudioActivityMonitor(Protocol):
    def start(self, on_status: StatusCallback) -> None:
        ...

    def stop(self) -> None:
        ...


class VoiceActivityDetector(Protocol):
    def is_speech(self, chunk: bytes) -> bool:
        ...
