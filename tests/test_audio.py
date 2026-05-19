import wave
from pathlib import Path

from pytest import MonkeyPatch

from translator.audio import (
    SegmentEndReason,
    SpeechSegmenter,
    WebRtcVoiceDetector,
    build_capture_command,
    rms_s16le,
    split_vad_frames,
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


def fake_which(command: str) -> str:
    return f"/usr/bin/{command}"


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
    speech_max_ms: int = 10_000,
    speech_overlap_ms: int = 1_000,
    debug_audio_dir: str | None = None,
) -> AppSettings:
    return AppSettings(
        audio_sample_rate=8_000,
        audio_chunk_frames=800,
        speech_start_ms=300,
        speech_end_ms=200,
        speech_max_ms=speech_max_ms,
        speech_overlap_ms=speech_overlap_ms,
        debug_audio_dir=debug_audio_dir,
    )


def audio_chunk() -> bytes:
    return b"\x01\x00" * 800


def silent_chunk() -> bytes:
    return b"\x00\x00" * 800


class FakeVad:
    def __init__(self, aggressiveness: int) -> None:
        self.aggressiveness = aggressiveness

    def is_speech(self, frame: bytes, sample_rate: int) -> bool:
        return sample_rate == 8_000 and frame.startswith(b"speech")


def build_fake_vad(aggressiveness: int) -> FakeVad:
    return FakeVad(aggressiveness)
