from __future__ import annotations

import importlib
from typing import Protocol, cast

from translator.config import AppSettings


class WebRtcVad(Protocol):
    def is_speech(
        self,
        buf: bytes,
        sample_rate: int,
        length: int | None = None,
    ) -> bool:
        ...


class WebRtcVadFactory(Protocol):
    def __call__(self, aggressiveness: int) -> WebRtcVad:
        ...


class WebRtcVoiceDetector:
    def __init__(self, settings: AppSettings) -> None:
        validate_vad_settings(settings)
        self._settings = settings
        self._vad = build_webrtc_vad(settings.vad_aggressiveness)
        self._frame_bytes = settings.audio_sample_rate * settings.vad_frame_ms // 1_000 * 2

    def is_speech(self, chunk: bytes) -> bool:
        speech_frames = 0
        total_frames = 0

        for frame in split_vad_frames(chunk, self._frame_bytes):
            total_frames += 1
            if self._vad.is_speech(frame, self._settings.audio_sample_rate):
                speech_frames += 1

        if total_frames == 0:
            return False

        return speech_frames / total_frames >= self._settings.vad_speech_ratio


def build_webrtc_vad(aggressiveness: int) -> WebRtcVad:
    module = importlib.import_module("webrtcvad")
    vad_factory = cast(WebRtcVadFactory, module.__dict__["Vad"])
    return vad_factory(aggressiveness)


def validate_vad_settings(settings: AppSettings) -> None:
    if settings.audio_sample_rate not in {8_000, 16_000, 32_000, 48_000}:
        msg = "WebRTC VAD requires an audio sample rate of 8000, 16000, 32000, or 48000"
        raise ValueError(msg)

    if settings.vad_frame_ms not in {10, 20, 30}:
        msg = "WebRTC VAD requires a frame size of 10, 20, or 30 ms"
        raise ValueError(msg)


def split_vad_frames(chunk: bytes, frame_bytes: int) -> list[bytes]:
    return [
        chunk[index : index + frame_bytes]
        for index in range(0, len(chunk) - frame_bytes + 1, frame_bytes)
    ]
