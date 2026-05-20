from pathlib import Path

from pytest import MonkeyPatch

from translator.config import AppSettings


def test_default_settings_are_valid(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)

    settings = AppSettings()

    assert settings.window_title == "Live Subtitles"
    assert settings.placeholder_text == "Waiting for audio..."
    assert settings.width == 960
    assert settings.height == 420
    assert settings.always_on_top is True
    assert settings.caption_timeout_seconds == 10
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
    assert settings.debug_transcript_path is None
    assert settings.transcription_enabled is True
    assert settings.whisper_model == "large-v3"
    assert settings.whisper_device == "cuda"
    assert settings.whisper_device_index == 0
    assert settings.whisper_compute_type == "float16"
    assert settings.whisper_language is None
    assert settings.whisper_task == "transcribe"
    assert settings.whisper_beam_size == 5
    assert settings.whisper_no_speech_threshold == 0.6
    assert settings.whisper_log_prob_threshold == -1.0
    assert settings.whisper_compression_ratio_threshold == 2.4
    assert settings.whisper_condition_on_previous_text is False
    assert settings.translation_enabled is False
    assert settings.translation_model == "facebook/nllb-200-distilled-600M"
    assert settings.translation_device == "cpu"
    assert settings.translation_device_index == 1
    assert settings.translation_compute_dtype == "float32"
    assert settings.translation_target_language == "eng_Latn"
    assert settings.translation_display_mode == "both"
    assert settings.translation_max_length == 512
    assert settings.translation_max_new_tokens == 128
    assert settings.translation_no_repeat_ngram_size == 3
    assert settings.translation_repetition_penalty == 1.15
    assert settings.translation_repeated_word_limit == 3


def test_settings_read_dotenv_file(tmp_path: Path, monkeypatch: MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text("TRANSLATOR_WIDTH=800\n", encoding="utf-8")

    settings = AppSettings()

    assert settings.width == 800


def test_settings_treat_optional_empty_strings_as_none(
    tmp_path: Path,
    monkeypatch: MonkeyPatch,
) -> None:
    monkeypatch.chdir(tmp_path)
    (tmp_path / ".env").write_text(
        "\n".join(
            [
                "TRANSLATOR_AUDIO_SOURCE=",
                "TRANSLATOR_DEBUG_AUDIO_DIR=",
                "TRANSLATOR_DEBUG_TRANSCRIPT_PATH=",
                "TRANSLATOR_WHISPER_LANGUAGE=",
            ]
        ),
        encoding="utf-8",
    )

    settings = AppSettings()

    assert settings.audio_source is None
    assert settings.debug_audio_dir is None
    assert settings.debug_transcript_path is None
    assert settings.whisper_language is None
