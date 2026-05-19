from __future__ import annotations

import shutil
import subprocess
import threading
from collections.abc import Callable
from enum import StrEnum
from math import sqrt
from typing import Protocol

from translator.config import AppSettings


class AudioStatus(StrEnum):
    CAPTURE_UNAVAILABLE = "Audio capture unavailable"
    LISTENING = "Listening..."
    SILENCE = "Silence"
    AUDIO_DETECTED = "Audio detected"


StatusCallback = Callable[[AudioStatus], None]


class AudioActivityMonitor(Protocol):
    def start(self, on_status: StatusCallback) -> None:
        ...

    def stop(self) -> None:
        ...


class PulseAudioActivityMonitor(AudioActivityMonitor):
    def __init__(self, settings: AppSettings) -> None:
        self._settings = settings
        self._process: subprocess.Popen[bytes] | None = None
        self._thread: threading.Thread | None = None
        self._stop_event = threading.Event()

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
        if self._process is not None:
            self._process.terminate()
            try:
                self._process.wait(timeout=1)
            except subprocess.TimeoutExpired:
                self._process.kill()
                self._process.wait(timeout=1)

        if self._thread is not None:
            self._thread.join(timeout=1)

    def _run(self, on_status: StatusCallback) -> None:
        command = build_capture_command(self._settings)
        if command is None:
            on_status(AudioStatus.CAPTURE_UNAVAILABLE)
            return

        try:
            self._process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
            )
        except OSError:
            on_status(AudioStatus.CAPTURE_UNAVAILABLE)
            return

        on_status(AudioStatus.LISTENING)
        chunk_bytes = self._settings.audio_chunk_frames * 2

        while not self._stop_event.is_set():
            if self._process.stdout is None:
                on_status(AudioStatus.CAPTURE_UNAVAILABLE)
                return

            chunk = self._process.stdout.read(chunk_bytes)
            if not chunk:
                on_status(AudioStatus.CAPTURE_UNAVAILABLE)
                return

            status = (
                AudioStatus.AUDIO_DETECTED
                if rms_s16le(chunk) >= self._settings.audio_detection_threshold
                else AudioStatus.SILENCE
            )
            on_status(status)


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


def rms_s16le(chunk: bytes) -> float:
    sample_count = len(chunk) // 2
    if sample_count == 0:
        return 0.0

    total = 0
    for index in range(0, sample_count * 2, 2):
        sample = int.from_bytes(chunk[index : index + 2], byteorder="little", signed=True)
        total += sample * sample

    return sqrt(total / sample_count) / 32_768
