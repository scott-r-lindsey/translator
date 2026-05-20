from __future__ import annotations

import shutil
import subprocess
import threading

from translator.audio_types import AudioStatus, StatusCallback, VoiceActivityDetector, status_event
from translator.config import AppSettings
from translator.pcm import rms_s16le
from translator.speech_segments import SpeechSegmenter
from translator.transcription import Transcriber, TranscriptionWorker, build_transcription_worker
from translator.voice_activity import WebRtcVoiceDetector


class PulseAudioActivityMonitor:
    def __init__(
        self,
        settings: AppSettings,
        voice_detector: VoiceActivityDetector | None = None,
        transcriber: Transcriber | None = None,
    ) -> None:
        self._settings = settings
        self._segmenter = SpeechSegmenter(settings)
        self._voice_detector = voice_detector or WebRtcVoiceDetector(settings)
        self._transcription_worker = build_audio_transcription_worker(settings, transcriber)
        self._process: subprocess.Popen[bytes] | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def prepare(self, on_status: StatusCallback) -> None:
        if self._transcription_worker is None:
            on_status(status_event(AudioStatus.READY.value))
            return

        self._transcription_worker.prepare(on_status)

    def start(self, on_status: StatusCallback) -> None:
        if self._thread is not None:
            return

        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._run,
            args=(on_status,),
            name="audio-activity-monitor",
            daemon=True,
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop_event.set()
        if self._transcription_worker is not None:
            self._transcription_worker.stop()

        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=1)

        if self._thread is not None:
            self._thread.join(timeout=1)
            self._thread = None

    def _run(self, on_status: StatusCallback) -> None:
        if self._transcription_worker is not None:
            self._transcription_worker.start(on_status)

        command = build_capture_command(self._settings)
        if command is None:
            on_status(status_event(AudioStatus.CAPTURE_UNAVAILABLE.value))
            return

        try:
            self._process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            on_status(status_event(AudioStatus.CAPTURE_UNAVAILABLE.value))
            return

        on_status(status_event(AudioStatus.LISTENING.value))
        chunk_bytes = self._settings.audio_chunk_frames * 2

        while not self._stop_event.is_set():
            if self._process.stdout is None:
                on_status(status_event(AudioStatus.CAPTURE_UNAVAILABLE.value))
                return

            chunk = self._process.stdout.read(chunk_bytes)
            if not chunk:
                on_status(status_event(AudioStatus.CAPTURE_UNAVAILABLE.value))
                return

            level = rms_s16le(chunk)
            is_audio_detected = level >= self._settings.audio_detection_threshold
            is_speech_detected = is_audio_detected and self._voice_detector.is_speech(chunk)
            segment = self._segmenter.process(chunk, is_speech_detected)
            if segment is not None and self._transcription_worker is not None:
                self._transcription_worker.submit(segment)

            if self._segmenter.is_speech_active:
                status = AudioStatus.SPEECH_DETECTED
            elif is_audio_detected:
                status = AudioStatus.AUDIO_DETECTED
            else:
                status = AudioStatus.SILENCE

            on_status(status_event(status.value))


def build_capture_command(settings: AppSettings) -> list[str] | None:
    parec = shutil.which("parec")
    if parec is None:
        return None

    source = settings.audio_source or default_monitor_source()
    command = [
        parec,
        "--raw",
        "--format=s16le",
        f"--rate={settings.audio_sample_rate}",
        "--channels=1",
    ]
    if source is not None:
        command.append(f"--device={source}")

    return command


def default_monitor_source() -> str | None:
    pactl = shutil.which("pactl")
    if pactl is None:
        return None

    try:
        result = subprocess.run(
            [pactl, "get-default-sink"],
            check=True,
            capture_output=True,
            text=True,
            timeout=2,
        )
    except (OSError, subprocess.SubprocessError):
        return None

    sink = result.stdout.strip()
    if not sink:
        return None

    return f"{sink}.monitor"


def build_audio_transcription_worker(
    settings: AppSettings,
    transcriber: Transcriber | None,
) -> TranscriptionWorker | None:
    if not settings.transcription_enabled:
        return None

    if transcriber is not None:
        return TranscriptionWorker(transcriber, settings.debug_transcript_path)

    return build_transcription_worker(settings)
