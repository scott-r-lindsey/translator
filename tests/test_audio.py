import wave
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from pytest import MonkeyPatch

from translator.audio import (
    AudioStatus,
    DisplayEvent,
    PulseAudioActivityMonitor,
    SegmentEndReason,
    SpeechSegment,
    SpeechSegmenter,
    StatusCallback,
    Transcription,
    WebRtcVoiceDetector,
    build_capture_command,
    rms_s16le,
    split_vad_frames,
    status_event,
    validate_vad_settings,
)
from translator.config import AppSettings


def test_rms_s16le_returns_zero_for_silence() -> None:
    assert rms_s16le(b"\x00\x00" * 4) == 0.0


def test_rms_s16le_detects_nonzero_audio() -> None:
    assert rms_s16le(b"\xff\x7f" * 4) > 0.9


def test_build_capture_command_uses_configured_source(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("translator.audio_capture.shutil.which", fake_which)
    settings = AppSettings(audio_source="alsa_output.test.monitor")

    command = build_capture_command(settings)

    assert command == [
        "/usr/bin/parec",
        "--raw",
        "--format=s16le",
        "--rate=16000",
        "--channels=1",
        "--device=alsa_output.test.monitor",
    ]


def test_pulseaudio_monitor_prepare_emits_ready_without_transcription() -> None:
    emitted: list[DisplayEvent] = []
    monitor = PulseAudioActivityMonitor(AppSettings(transcription_enabled=False))

    monitor.prepare(emitted.append)

    assert [event.text for event in emitted] == [AudioStatus.READY.value]


def test_pulseaudio_monitor_prepare_delegates_to_transcription_worker(
    monkeypatch: MonkeyPatch,
) -> None:
    worker = FakeTranscriptionWorker()
    monkeypatch.setattr(
        "translator.audio_capture.build_audio_transcription_worker",
        build_fake_transcription_worker(worker),
    )
    monitor = PulseAudioActivityMonitor(AppSettings())
    emitted: list[DisplayEvent] = []

    monitor.prepare(emitted.append)

    assert worker.prepared is True
    assert [event.text for event in emitted] == ["worker-ready"]


def test_pulseaudio_monitor_start_ignores_duplicate_starts(monkeypatch: MonkeyPatch) -> None:
    threads: list[FakeThread] = []

    def build_thread(**kwargs: object) -> "FakeThread":
        thread = FakeThread(**kwargs)
        threads.append(thread)
        return thread

    monkeypatch.setattr("translator.audio_capture.threading.Thread", build_thread)
    monitor = PulseAudioActivityMonitor(AppSettings(transcription_enabled=False))

    monitor.start(lambda _event: None)
    monitor.start(lambda _event: None)

    assert len(threads) == 1
    assert threads[0].started is True


def test_pulseaudio_monitor_stop_terminates_process_and_clears_thread() -> None:
    monitor = PulseAudioActivityMonitor(AppSettings(transcription_enabled=False))
    process = FakeProcess([b""])
    thread = FakeThread()
    monitor_for_test = cast(Any, monitor)
    monitor_for_test._process = process
    monitor_for_test._thread = thread

    monitor.stop()

    assert process.terminated is True
    assert process.killed is False
    assert thread.joined is True
    assert monitor_for_test._thread is None


def test_pulseaudio_monitor_run_reports_unavailable_without_capture_command(
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.setattr("translator.audio_capture.build_capture_command", no_capture_command)
    monitor = PulseAudioActivityMonitor(AppSettings(transcription_enabled=False))
    emitted: list[DisplayEvent] = []

    cast(Any, monitor)._run(emitted.append)

    assert [event.text for event in emitted] == [AudioStatus.CAPTURE_UNAVAILABLE.value]


def test_pulseaudio_monitor_run_reports_audio_and_speech_statuses(
    monkeypatch: MonkeyPatch,
) -> None:
    process = FakeProcess([silent_chunk(), loud_chunk(), loud_chunk(), loud_chunk(), b""])
    monkeypatch.setattr(
        "translator.audio_capture.build_capture_command",
        fake_capture_command,
    )
    monkeypatch.setattr(
        "translator.audio_capture.subprocess.Popen",
        build_fake_popen(process),
    )
    monitor = PulseAudioActivityMonitor(
        segmenter_settings(speech_start_ms=200, audio_detection_threshold=0.01),
        voice_detector=AlwaysSpeechDetector(),
        transcriber=FakeTranscriber(),
    )
    emitted: list[DisplayEvent] = []

    cast(Any, monitor)._run(emitted.append)

    assert [event.text for event in emitted] == [
        AudioStatus.READY.value,
        AudioStatus.LISTENING.value,
        AudioStatus.SILENCE.value,
        AudioStatus.AUDIO_DETECTED.value,
        AudioStatus.SPEECH_DETECTED.value,
        AudioStatus.SPEECH_DETECTED.value,
        AudioStatus.CAPTURE_UNAVAILABLE.value,
    ]


def fake_which(command: str) -> str:
    return f"/usr/bin/{command}"


def build_fake_transcription_worker(
    worker: "FakeTranscriptionWorker",
) -> Callable[[AppSettings, object], "FakeTranscriptionWorker"]:
    def build_worker(
        _settings: AppSettings,
        _transcriber: object,
    ) -> FakeTranscriptionWorker:
        return worker

    return build_worker


def no_capture_command(_settings: AppSettings) -> None:
    return None


def fake_capture_command(_settings: AppSettings) -> list[str]:
    return ["/usr/bin/parec"]


def build_fake_popen(process: "FakeProcess") -> Callable[..., "FakeProcess"]:
    def popen(*_args: object, **_kwargs: object) -> FakeProcess:
        return process

    return popen


def test_split_vad_frames_discards_partial_trailing_frame() -> None:
    assert split_vad_frames(b"abcdefghi", frame_bytes=3) == [b"abc", b"def", b"ghi"]
    assert split_vad_frames(b"abcdefghij", frame_bytes=3) == [b"abc", b"def", b"ghi"]


def test_validate_vad_settings_rejects_unsupported_sample_rate() -> None:
    settings = AppSettings(audio_sample_rate=44_100)

    try:
        validate_vad_settings(settings)
    except ValueError as error:
        assert "sample rate" in str(error)
    else:
        raise AssertionError("Expected invalid sample rate to fail")


def test_webrtc_voice_detector_uses_configured_speech_ratio(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("translator.voice_activity.build_webrtc_vad", build_fake_vad)
    detector = WebRtcVoiceDetector(
        AppSettings(
            audio_sample_rate=8_000,
            vad_aggressiveness=3,
            vad_frame_ms=10,
            vad_speech_ratio=0.5,
        )
    )

    speech_frame = b"speech" + (b"_" * 154)
    quiet_frame = b"quiet" + (b"_" * 155)

    assert detector.is_speech(speech_frame + quiet_frame) is True
    assert detector.is_speech(quiet_frame + quiet_frame) is False


def test_speech_segmenter_starts_after_sustained_audio() -> None:
    segmenter = SpeechSegmenter(segmenter_settings())

    assert segmenter.process(audio_chunk(), is_speech_detected=True) is None
    assert segmenter.is_speech_active is False

    assert segmenter.process(audio_chunk(), is_speech_detected=True) is None
    assert segmenter.is_speech_active is False

    assert segmenter.process(audio_chunk(), is_speech_detected=True) is None
    assert segmenter.is_speech_active is True


def test_speech_segmenter_finishes_after_sustained_silence() -> None:
    segmenter = SpeechSegmenter(segmenter_settings())

    for _ in range(3):
        assert segmenter.process(audio_chunk(), is_speech_detected=True) is None

    assert segmenter.process(silent_chunk(), is_speech_detected=False) is None
    segment = segmenter.process(silent_chunk(), is_speech_detected=False)

    assert segment is not None
    assert segment.end_reason is SegmentEndReason.SILENCE
    assert segment.duration_ms == 500
    assert len(segment.pcm) == len(audio_chunk()) * 5
    assert segmenter.is_speech_active is False


def test_speech_segmenter_finishes_at_max_segment_length() -> None:
    segmenter = SpeechSegmenter(segmenter_settings(speech_max_ms=1_000, speech_overlap_ms=200))
    segment = None

    for _ in range(10):
        segment = segmenter.process(audio_chunk(), is_speech_detected=True)

    assert segment is not None
    assert segment.end_reason is SegmentEndReason.MAX_DURATION
    assert segment.duration_ms == 1_000
    assert len(segment.pcm) == len(audio_chunk()) * 10
    assert segmenter.is_speech_active is True


def test_speech_segmenter_includes_overlap_after_max_segment_length() -> None:
    segmenter = SpeechSegmenter(segmenter_settings(speech_max_ms=1_000, speech_overlap_ms=200))

    first_segment = None
    for _ in range(10):
        first_segment = segmenter.process(audio_chunk(), is_speech_detected=True)

    assert first_segment is not None
    second_segment = None
    for _ in range(8):
        second_segment = segmenter.process(audio_chunk(), is_speech_detected=True)

    assert second_segment is not None
    assert second_segment.end_reason is SegmentEndReason.MAX_DURATION
    assert second_segment.duration_ms == 1_000
    assert len(second_segment.pcm) == len(audio_chunk()) * 10


def test_speech_segmenter_writes_debug_wav(tmp_path: Path) -> None:
    segmenter = SpeechSegmenter(segmenter_settings(debug_audio_dir=str(tmp_path)))

    for _ in range(3):
        segmenter.process(audio_chunk(), is_speech_detected=True)

    segmenter.process(silent_chunk(), is_speech_detected=False)
    segmenter.process(silent_chunk(), is_speech_detected=False)

    wav_path = tmp_path / "segment-0001-silence.wav"
    assert wav_path.exists()
    with wave.open(str(wav_path), "rb") as wav_file:
        assert wav_file.getnchannels() == 1
        assert wav_file.getsampwidth() == 2
        assert wav_file.getframerate() == 8_000
        assert wav_file.getnframes() == 4_000


def segmenter_settings(
    *,
    audio_detection_threshold: float = 0.01,
    speech_start_ms: int = 300,
    speech_max_ms: int = 10_000,
    speech_overlap_ms: int = 1_000,
    debug_audio_dir: str | None = None,
) -> AppSettings:
    return AppSettings(
        audio_sample_rate=8_000,
        audio_chunk_frames=800,
        audio_detection_threshold=audio_detection_threshold,
        speech_start_ms=speech_start_ms,
        speech_end_ms=200,
        speech_max_ms=speech_max_ms,
        speech_overlap_ms=speech_overlap_ms,
        debug_audio_dir=debug_audio_dir,
    )


def audio_chunk() -> bytes:
    return b"\x01\x00" * 800


def silent_chunk() -> bytes:
    return b"\x00\x00" * 800


def loud_chunk() -> bytes:
    return b"\xff\x7f" * 800


class FakeVad:
    def __init__(self, aggressiveness: int) -> None:
        self.aggressiveness = aggressiveness

    def is_speech(self, frame: bytes, sample_rate: int) -> bool:
        return sample_rate == 8_000 and frame.startswith(b"speech")


def build_fake_vad(aggressiveness: int) -> FakeVad:
    return FakeVad(aggressiveness)


class FakeTranscriber:
    def transcribe(self, segment: SpeechSegment) -> Transcription:
        assert segment.sample_rate == 8_000
        return Transcription(text="done")


class FakeTranscriptionWorker:
    def __init__(self) -> None:
        self.prepared = False

    def prepare(self, on_status: StatusCallback) -> None:
        self.prepared = True
        on_status(status_event("worker-ready"))


class FakeThread:
    def __init__(self, **_kwargs: object) -> None:
        self.started = False
        self.joined = False

    def start(self) -> None:
        self.started = True

    def join(self, timeout: float | None = None) -> None:
        self.joined = timeout == 1


class FakeStdout:
    def __init__(self, chunks: list[bytes]) -> None:
        self._chunks = chunks

    def read(self, _size: int) -> bytes:
        if not self._chunks:
            return b""

        return self._chunks.pop(0)


class FakeProcess:
    def __init__(self, chunks: list[bytes]) -> None:
        self.stdout = FakeStdout(chunks)
        self.terminated = False
        self.killed = False

    def terminate(self) -> None:
        self.terminated = True

    def kill(self) -> None:
        self.killed = True

    def wait(self, timeout: float | None = None) -> int:
        assert timeout == 1
        return 0


class AlwaysSpeechDetector:
    def is_speech(self, chunk: bytes) -> bool:
        assert chunk
        return True
