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
