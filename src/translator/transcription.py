from __future__ import annotations

import importlib
import logging
import threading
from dataclasses import dataclass
from queue import Queue
from typing import Any, Protocol, cast

import numpy as np
from numpy.typing import NDArray

from translator.audio_types import AudioStatus, StatusCallback
from translator.config import AppSettings
from translator.speech_segments import SpeechSegment

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Transcription:
    text: str
    language: str | None = None


class Transcriber(Protocol):
    def transcribe(self, segment: SpeechSegment) -> Transcription:
        ...


class WhisperSegment(Protocol):
    text: str


class WhisperInfo(Protocol):
    language: str | None


class WhisperModelProtocol(Protocol):
    def transcribe(
        self,
        audio: NDArray[np.float32],
        *,
        language: str | None,
        task: str,
        beam_size: int,
    ) -> tuple[object, WhisperInfo]:
        ...


class WhisperModelFactory(Protocol):
    def __call__(
        self,
        model_size_or_path: str,
        *,
        device: str,
        device_index: int,
        compute_type: str,
    ) -> WhisperModelProtocol:
        ...


class FasterWhisperTranscriber:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._model: WhisperModelProtocol | None = None

    def transcribe(self, segment: SpeechSegment) -> Transcription:
        model = self._load_model()
        audio = pcm_s16le_to_float32(segment.pcm)
        raw_segments, info = model.transcribe(
            audio,
            language=self._settings.whisper_language,
            task=self._settings.whisper_task,
            beam_size=self._settings.whisper_beam_size,
        )
        text = " ".join(
            whisper_segment.text.strip()
            for whisper_segment in iter_whisper_segments(raw_segments)
            if whisper_segment.text.strip()
        )
        return Transcription(text=text, language=info.language)

    def _load_model(self) -> WhisperModelProtocol:
        if self._model is None:
            self._model = build_whisper_model(
                self._settings.whisper_model,
                device=self._settings.whisper_device,
                device_index=self._settings.whisper_device_index,
                compute_type=self._settings.whisper_compute_type,
            )

        return self._model


class TranscriptionWorker:
    def __init__(self, transcriber: Transcriber) -> None:
        self._transcriber = transcriber
        self._queue: Queue[SpeechSegment | None] = Queue()
        self._thread: threading.Thread | None = None
        self._callback: StatusCallback | None = None

    def start(self, on_status: StatusCallback) -> None:
        if self._thread is not None:
            return

        self._callback = on_status
        self._thread = threading.Thread(
            target=self._run,
            name="transcription-worker",
            daemon=True,
        )
        self._thread.start()

    def submit(self, segment: SpeechSegment) -> None:
        self._queue.put(segment)

    def stop(self) -> None:
        if self._thread is None:
            return

        self._queue.put(None)
        self._thread.join(timeout=2)

    def _run(self) -> None:
        while True:
            segment = self._queue.get()
            if segment is None:
                return

            self._emit(AudioStatus.TRANSCRIBING)
            try:
                transcription = self._transcriber.transcribe(segment)
            except Exception as error:
                LOGGER.exception("Transcription failed")
                self._emit(f"{AudioStatus.TRANSCRIPTION_UNAVAILABLE.value}: {error}")
                continue

            if transcription.text:
                self._emit(transcription.text)

    def _emit(self, text: str) -> None:
        if self._callback is not None:
            self._callback(text)


def build_whisper_model(
    model: str,
    *,
    device: str,
    device_index: int,
    compute_type: str,
) -> WhisperModelProtocol:
    module = importlib.import_module("faster_whisper")
    model_factory = cast(WhisperModelFactory, module.__dict__["WhisperModel"])
    return model_factory(
        model,
        device=device,
        device_index=device_index,
        compute_type=compute_type,
    )


def iter_whisper_segments(raw_segments: object) -> list[WhisperSegment]:
    return [cast(WhisperSegment, segment) for segment in cast(Any, raw_segments)]


def pcm_s16le_to_float32(pcm: bytes) -> NDArray[np.float32]:
    int_audio = np.frombuffer(pcm, dtype=np.int16)
    return np.divide(int_audio.astype(np.float32), np.float32(32_768)).copy()
