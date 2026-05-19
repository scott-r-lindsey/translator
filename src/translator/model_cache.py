from __future__ import annotations

from translator.config import AppSettings
from translator.transcription import verify_whisper_model
from translator.translation import build_nllb_model


def download_configured_models(settings: AppSettings) -> None:
    if not settings.transcription_enabled:
        print("Transcription disabled; no transcription models to download.")
        return

    print(
        "Loading Whisper model "
        f"model={settings.whisper_model} "
        f"device={settings.whisper_device} "
        f"device_index={settings.whisper_device_index} "
        f"compute_type={settings.whisper_compute_type}"
    )
    verify_whisper_model(settings)
    print("Whisper model is available.")

    if settings.translation_enabled:
        print(
            "Loading translation model "
            f"model={settings.translation_model} "
            f"device={settings.translation_device} "
            f"device_index={settings.translation_device_index} "
            f"dtype={settings.translation_compute_dtype}"
        )
        build_nllb_model(settings)
        print("Translation model is available.")


def main() -> None:
    download_configured_models(AppSettings())


if __name__ == "__main__":
    main()
