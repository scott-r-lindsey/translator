from __future__ import annotations

import wave
from dataclasses import dataclass
from pathlib import Path

from translator.audio_types import SegmentEndReason
from translator.config import AppSettings


@dataclass(frozen=True)
class SpeechSegment:
    pcm: bytes
    sample_rate: int
    end_reason: SegmentEndReason


class SpeechSegmenter:
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._chunk_ms = settings.audio_chunk_frames / settings.audio_sample_rate * 1_000
        self._is_speech_active = False
        self._voiced_ms = 0.0
        self._silent_ms = 0.0
        self._segment_ms = 0.0
        self._pending_chunks: list[bytes] = []
        self._segment_chunks: list[bytes] = []
        self._debug_segment_count = 0

    @property
    def is_speech_active(self) -> bool:
        return self._is_speech_active

    def process(self, chunk: bytes, is_speech_detected: bool) -> SpeechSegment | None:
        if is_speech_detected:
            return self._process_speech_chunk(chunk)

        return self._process_silent_chunk(chunk)

    def _process_speech_chunk(self, chunk: bytes) -> SpeechSegment | None:
        self._voiced_ms += self._chunk_ms
        self._silent_ms = 0.0

        if not self._is_speech_active:
            self._pending_chunks.append(chunk)
            if self._voiced_ms >= self._settings.speech_start_ms:
                self._is_speech_active = True
                self._segment_chunks = list(self._pending_chunks)
                self._segment_ms = len(self._segment_chunks) * self._chunk_ms
                self._pending_chunks.clear()
            return None

        self._segment_chunks.append(chunk)
        self._segment_ms += self._chunk_ms
        return self._finish_if_too_long()

    def _process_silent_chunk(self, chunk: bytes) -> SpeechSegment | None:
        self._voiced_ms = 0.0
        self._pending_chunks.clear()

        if not self._is_speech_active:
            return None

        self._segment_chunks.append(chunk)
        self._segment_ms += self._chunk_ms
        self._silent_ms += self._chunk_ms

        if self._silent_ms >= self._settings.speech_end_ms:
            return self._finish_segment(SegmentEndReason.SILENCE)

        return self._finish_if_too_long()

    def _finish_if_too_long(self) -> SpeechSegment | None:
        if self._segment_ms >= self._settings.speech_max_ms:
            return self._finish_segment(SegmentEndReason.MAX_DURATION)

        return None

    def _finish_segment(self, end_reason: SegmentEndReason) -> SpeechSegment:
        segment = SpeechSegment(
            pcm=b"".join(self._segment_chunks),
            sample_rate=self._settings.audio_sample_rate,
            end_reason=end_reason,
        )
        self._write_debug_segment(segment)

        if end_reason is SegmentEndReason.MAX_DURATION:
            self._reset_to_overlap()
        else:
            self._reset()

        return segment

    def _reset_to_overlap(self) -> None:
        overlap_chunk_count = round(self._settings.speech_overlap_ms / self._chunk_ms)
        overlap_chunks = (
            self._segment_chunks[-overlap_chunk_count:] if overlap_chunk_count > 0 else []
        )

        self._is_speech_active = bool(overlap_chunks)
        self._voiced_ms = len(overlap_chunks) * self._chunk_ms
        self._silent_ms = 0.0
        self._segment_ms = len(overlap_chunks) * self._chunk_ms
        self._segment_chunks = list(overlap_chunks)
        self._pending_chunks.clear()

    def _reset(self) -> None:
        self._is_speech_active = False
        self._voiced_ms = 0.0
        self._silent_ms = 0.0
        self._segment_ms = 0.0
        self._segment_chunks.clear()
        self._pending_chunks.clear()

    def _write_debug_segment(self, segment: SpeechSegment) -> None:
        if self._settings.debug_audio_dir is None:
            return

        debug_dir = Path(self._settings.debug_audio_dir)
        debug_dir.mkdir(parents=True, exist_ok=True)
        self._debug_segment_count += 1
        path = debug_dir / f"segment-{self._debug_segment_count:04d}-{segment.end_reason}.wav"

        with wave.open(str(path), "wb") as wav_file:
            wav_file.setnchannels(1)
            wav_file.setsampwidth(2)
            wav_file.setframerate(segment.sample_rate)
            wav_file.writeframes(segment.pcm)
