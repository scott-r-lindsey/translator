from pytest import MonkeyPatch

from translator.config import AppSettings
from translator.model_cache import download_configured_models


def test_download_configured_models_loads_whisper_model(monkeypatch: MonkeyPatch) -> None:
    calls: list[tuple[str, str, int, str]] = []

    def build_model(
        model: str,
        *,
        device: str,
        device_index: int,
        compute_type: str,
    ) -> object:
        calls.append((model, device, device_index, compute_type))
        return object()

    monkeypatch.setattr("translator.model_cache.build_whisper_model", build_model)

    download_configured_models(
        AppSettings(
            whisper_model="large-v3",
            whisper_device="cuda",
            whisper_device_index=1,
            whisper_compute_type="int8_float16",
        )
    )

    assert calls == [("large-v3", "cuda", 1, "int8_float16")]


def test_download_configured_models_skips_when_transcription_disabled(
    monkeypatch: MonkeyPatch,
) -> None:
    def fail_build_model(
        _model: str,
        *,
        device: str,
        device_index: int,
        compute_type: str,
    ) -> object:
        raise AssertionError("model should not be loaded")

    monkeypatch.setattr("translator.model_cache.build_whisper_model", fail_build_model)

    download_configured_models(AppSettings(transcription_enabled=False))
