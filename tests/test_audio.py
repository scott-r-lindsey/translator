from pytest import MonkeyPatch

from translator.audio import build_capture_command, rms_s16le
from translator.config import AppSettings


def test_rms_s16le_returns_zero_for_silence() -> None:
    assert rms_s16le(b"\x00\x00" * 4) == 0.0


def test_rms_s16le_detects_nonzero_audio() -> None:
    assert rms_s16le(b"\xff\x7f" * 4) > 0.9


def test_build_capture_command_uses_configured_source(monkeypatch: MonkeyPatch) -> None:
    monkeypatch.setattr("translator.audio.shutil.which", fake_which)
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
