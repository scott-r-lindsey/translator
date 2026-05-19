from pathlib import Path

from pytest import MonkeyPatch

from translator.audio import SegmentEndReason
from translator.config import AppSettings
from translator.speech_segments import SpeechSegment
from translator.transcription import (
    FasterWhisperTranscriber,
    Transcription,
    TranscriptionWorker,
    pcm_s16le_to_float32,
    write_debug_transcript,
)


class FakeWhisperSegment:
    def __init__(self, text: str) -> None:
        self.text = text


class FakeWhisperInfo:
    def __init__(self, language: str | None) -> None:
        self.language = language


class FakeWhisperModel:
    def transcribe(
        self,
        _audio: object,
        *,
        language: str | None,
        task: str,
        beam_size: int,
    ) -> tuple[list[FakeWhisperSegment], FakeWhisperInfo]:
        assert language is None
        assert task == "transcribe"
        assert beam_size == 5
        return [FakeWhisperSegment(" hello "), FakeWhisperSegment("world")], FakeWhisperInfo("en")


class FakeTranscriber:
    def transcribe(self, segment: SpeechSegment) -> Transcription:
        assert segment.sample_rate == 16_000
        return Transcription(text="done", language="en", latency_ms=250.0)


class FailingTranscriber:
    def transcribe(self, segment: SpeechSegment) -> Transcription:
        assert segment.sample_rate == 16_000
        raise RuntimeError("no cuda")


def test_pcm_s16le_to_float32_normalizes_audio() -> None:
    audio = pcm_s16le_to_float32(b"\x00\x00\xff\x7f\x00\x80")

    assert audio.tolist() == [0.0, 32767 / 32768, -1.0]


def test_faster_whisper_transcriber_uses_configured_model(monkeypatch: MonkeyPatch) -> None:
    calls: list[tuple[str, str, int, str]] = []

    def build_model(
        model: str,
        *,
        device: str,
        device_index: int,
        compute_type: str,
    ) -> FakeWhisperModel:
        calls.append((model, device, device_index, compute_type))
        return FakeWhisperModel()

    monkeypatch.setattr("translator.transcription.build_whisper_model", build_model)
    transcriber = FasterWhisperTranscriber(
        AppSettings(
            whisper_model="large-v3",
            whisper_device="cuda",
            whisper_device_index=1,
            whisper_compute_type="float16",
            whisper_language=None,
        )
    )

    transcription = transcriber.transcribe(speech_segment())

    assert calls == [("large-v3", "cuda", 1, "float16")]
    assert transcription.text == "hello world"
    assert transcription.language == "en"
    assert transcription.latency_ms > 0


def test_transcription_worker_emits_status_and_text() -> None:
    emitted: list[str] = []
    worker = TranscriptionWorker(FakeTranscriber())

    worker.start(emitted.append)
    worker.submit(speech_segment())
    worker.stop()

    assert emitted == ["Transcribing 0.1s...", "done"]


def test_transcription_worker_emits_failure_details() -> None:
    emitted: list[str] = []
    worker = TranscriptionWorker(FailingTranscriber())

    worker.start(emitted.append)
    worker.submit(speech_segment())
    worker.stop()

    assert emitted == ["Transcribing 0.1s...", "Transcription unavailable: no cuda"]


def test_transcription_worker_writes_debug_transcript(tmp_path: Path) -> None:
    emitted: list[str] = []
    transcript_path = tmp_path / "transcript.txt"
    worker = TranscriptionWorker(FakeTranscriber(), str(transcript_path))

    worker.start(emitted.append)
    worker.submit(speech_segment())
    worker.stop()

    contents = transcript_path.read_text(encoding="utf-8")
    assert "duration=0.1s" in contents
    assert "reason=silence" in contents
    assert "language=en" in contents
    assert "latency=0.25s" in contents
    assert "done" in contents


def test_write_debug_transcript_ignores_missing_path() -> None:
    write_debug_transcript(None, speech_segment(), Transcription(text="ignored"))


def speech_segment() -> SpeechSegment:
    return SpeechSegment(
        pcm=b"\x00\x00" * 1600,
        sample_rate=16_000,
        end_reason=SegmentEndReason.SILENCE,
        duration_ms=100.0,
    )
