from pytest import MonkeyPatch

from translator.config import AppSettings
from translator.model_cache import download_configured_models


def test_download_configured_models_loads_whisper_model(monkeypatch: MonkeyPatch) -> None:
    calls: list[tuple[str, str, int, str]] = []

    def verify_model(settings: AppSettings) -> None:
        calls.append(
            (
                settings.whisper_model,
                settings.whisper_device,
                settings.whisper_device_index,
                settings.whisper_compute_type,
            )
        )

    monkeypatch.setattr("translator.model_cache.verify_whisper_model", verify_model)

    download_configured_models(
        AppSettings(
            whisper_model="large-v3",
            whisper_device="cuda",
            whisper_device_index=1,
            whisper_compute_type="float16",
        )
    )

    assert calls == [("large-v3", "cuda", 1, "float16")]


def test_download_configured_models_loads_translation_model_when_enabled(
    monkeypatch: MonkeyPatch,
) -> None:
    whisper_calls = 0
    translation_calls = 0

    def verify_whisper_model(_settings: AppSettings) -> None:
        nonlocal whisper_calls
        whisper_calls += 1

    def build_translation_model(_settings: AppSettings) -> tuple[object, object]:
        nonlocal translation_calls
        translation_calls += 1
        return object(), object()

    monkeypatch.setattr("translator.model_cache.verify_whisper_model", verify_whisper_model)
    monkeypatch.setattr("translator.model_cache.build_nllb_model", build_translation_model)

    download_configured_models(AppSettings(translation_enabled=True))

    assert whisper_calls == 1
    assert translation_calls == 1


def test_download_configured_models_skips_when_transcription_disabled(
    monkeypatch: MonkeyPatch,
) -> None:
    def fail_verify_model(_settings: AppSettings) -> None:
        raise AssertionError("model should not be loaded")

    monkeypatch.setattr("translator.model_cache.verify_whisper_model", fail_verify_model)

    download_configured_models(AppSettings(transcription_enabled=False))
