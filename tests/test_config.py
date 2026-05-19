from pathlib import Path

from pytest import MonkeyPatch

from translator.config import AppSettings


def test_default_settings_are_valid() -> None:
    settings = AppSettings()

    assert settings.window_title == "Live Subtitles"
    assert settings.placeholder_text == "Waiting for audio..."
    assert settings.width == 640
    assert settings.height == 160
    assert settings.always_on_top is True
    assert settings.audio_source is None
    assert settings.audio_sample_rate == 16_000
    assert settings.audio_chunk_frames == 1_600
    assert settings.audio_detection_threshold == 0.01
    assert settings.speech_start_ms == 300
    assert settings.speech_end_ms == 800
    assert settings.speech_max_ms == 10_000
    assert settings.speech_overlap_ms == 1_000
    assert settings.vad_aggressiveness == 2
    assert settings.vad_frame_ms == 30
    assert settings.vad_speech_ratio == 0.5
    assert settings.debug_audio_dir is None


def test_settings_read_dotenv_file(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("TRANSLATOR_WIDTH=800\n", encoding="utf-8")

    settings = AppSettings()

    assert settings.width == 800
