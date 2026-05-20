from __future__ import annotations

import importlib
import logging
import threading
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from queue import Queue
from typing import Any, Protocol, cast

import numpy as np
from numpy.typing import NDArray

from translator.audio_types import AudioStatus, StatusCallback, caption_event, status_event
from translator.config import AppSettings
from translator.speech_segments import SpeechSegment
from translator.translation import (
    NllbTranslator,
    Translation,
    Translator,
    render_translation,
)

LOGGER = logging.getLogger(__name__)


@dataclass(frozen=True)
class Transcription:
    text: str
    language: str | None = None
    latency_ms: float = 0.0


class Transcriber(Protocol):
    def transcribe(self, segment: SpeechSegment) -> Transcription:
        ...


class Preloadable(Protocol):
    def prepare(self) -> None:
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
        started_at = time.perf_counter()
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
        latency_ms = (time.perf_counter() - started_at) * 1_000
        return Transcription(text=text, language=info.language, latency_ms=latency_ms)

    def prepare(self) -> None:
        self._load_model()

    def _load_model(self) -> WhisperModelProtocol:
        if self._model is None:
            LOGGER.info(
                "Loading Whisper model model=%s device=%s device_index=%s compute_type=%s",
                self._settings.whisper_model,
                self._settings.whisper_device,
                self._settings.whisper_device_index,
                self._settings.whisper_compute_type,
            )
            self._model = build_whisper_model(
                self._settings.whisper_model,
                device=self._settings.whisper_device,
                device_index=self._settings.whisper_device_index,
                compute_type=self._settings.whisper_compute_type,
            )

        return self._model


class TranscriptionWorker:
    def __init__(
        self,
        transcriber: Transcriber,
        debug_transcript_path: str | None = None,
        translator: Translator | None = None,
        translation_display_mode: str = "original",
    ) -> None:
        self._transcriber = transcriber
        self._debug_transcript_path = debug_transcript_path
        self._translator = translator
        self._translation_display_mode = translation_display_mode
        self._queue: Queue[SpeechSegment | None] = Queue()
        self._thread: threading.Thread | None = None
        self._callback: StatusCallback | None = None
        self._prepared = False

    def start(self, on_status: StatusCallback) -> None:
        if self._thread is not None:
            return

        self._callback = on_status
        self.prepare(on_status)
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
        self._thread = None

    def prepare(self, on_status: StatusCallback) -> None:
        self._callback = on_status
        if self._prepared:
            return

        self._prepare_models()
        self._prepared = True

    def _run(self) -> None:
        while True:
            segment = self._queue.get()
            if segment is None:
                return

            self._emit_status(f"Transcribing {segment.duration_ms / 1_000:.1f}s...")
            try:
                transcription = self._transcriber.transcribe(segment)
            except Exception as error:
                LOGGER.exception("Transcription failed")
                self._emit_status(f"{AudioStatus.TRANSCRIPTION_UNAVAILABLE.value}: {error}")
                continue

            translation = self._translate(transcription)
            LOGGER.info(
                "Transcribed segment duration_ms=%.0f end_reason=%s language=%s "
                "latency_ms=%.0f text_length=%s translation_latency_ms=%s",
                segment.duration_ms,
                segment.end_reason,
                transcription.language,
                transcription.latency_ms,
                len(transcription.text),
                f"{translation.latency_ms:.0f}" if translation is not None else "none",
            )
            write_debug_transcript(
                self._debug_transcript_path,
                segment,
                transcription,
                translation,
            )
            if transcription.text:
                rendered = render_translation(
                    transcription,
                    translation,
                    self._translation_display_mode,
                )
                translated_text = translation.translated_text if translation is not None else ""
                if self._translation_display_mode == "translation":
                    self._emit_caption("", rendered)
                elif self._translation_display_mode == "original":
                    self._emit_caption(rendered, "")
                else:
                    self._emit_caption(transcription.text, translated_text)

    def _emit_status(self, text: str) -> None:
        if self._callback is not None:
            self._callback(status_event(text))

    def _emit_caption(self, source_text: str, translated_text: str) -> None:
        if self._callback is not None:
            self._callback(caption_event(source_text, translated_text))

    def _prepare_models(self) -> None:
        self._prepare_model("Loading Whisper model...", self._transcriber)
        if self._translator is not None:
            self._prepare_model("Loading translation model...", self._translator)
        self._emit_status(AudioStatus.READY.value)

    def _prepare_model(self, message: str, model: object) -> None:
        if not hasattr(model, "prepare"):
            return

        self._emit_status(message)
        cast(Preloadable, model).prepare()

    def _translate(self, transcription: Transcription) -> Translation | None:
        if self._translator is None:
            return None

        return self._translator.translate(transcription)


def build_transcription_worker(settings: AppSettings) -> TranscriptionWorker:
    translator = NllbTranslator(settings) if settings.translation_enabled else None
    return TranscriptionWorker(
        FasterWhisperTranscriber(settings),
        settings.debug_transcript_path,
        translator,
        settings.translation_display_mode,
    )


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


def verify_whisper_model(settings: AppSettings) -> None:
    model = build_whisper_model(
        settings.whisper_model,
        device=settings.whisper_device,
        device_index=settings.whisper_device_index,
        compute_type=settings.whisper_compute_type,
    )
    silence = np.zeros(settings.audio_sample_rate, dtype=np.float32)
    segments, _info = model.transcribe(
        silence,
        language=settings.whisper_language,
        task=settings.whisper_task,
        beam_size=1,
    )
    for _segment in iter_whisper_segments(segments):
        break


def write_debug_transcript(
    path: str | None,
    segment: SpeechSegment,
    transcription: Transcription,
    translation: Translation | None = None,
) -> None:
    if path is None:
        return

    transcript_path = Path(path)
    transcript_path.parent.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).isoformat(timespec="seconds")
    language = transcription.language or "unknown"
    record = (
        f"[{timestamp}] duration={segment.duration_ms / 1_000:.1f}s "
        f"reason={segment.end_reason} language={language} "
        f"latency={transcription.latency_ms / 1_000:.2f}s\n"
        f"{transcription.text}\n\n"
    )
    if translation is not None:
        record = (
            f"[{timestamp}] duration={segment.duration_ms / 1_000:.1f}s "
            f"reason={segment.end_reason} language={language} "
            f"latency={transcription.latency_ms / 1_000:.2f}s "
            f"target={translation.target_language} "
            f"translation_latency={translation.latency_ms / 1_000:.2f}s\n"
            f"{translation.source_text}\n"
            f"{translation.translated_text}\n\n"
        )

    with transcript_path.open("a", encoding="utf-8") as transcript_file:
        transcript_file.write(record)


def iter_whisper_segments(raw_segments: object) -> list[WhisperSegment]:
    return [cast(WhisperSegment, segment) for segment in cast(Any, raw_segments)]


def pcm_s16le_to_float32(pcm: bytes) -> NDArray[np.float32]:
    int_audio = np.frombuffer(pcm, dtype=np.int16)
    return np.divide(int_audio.astype(np.float32), np.float32(32_768)).copy()
