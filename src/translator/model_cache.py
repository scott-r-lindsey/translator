from __future__ import annotations

from translator.config import AppSettings
from translator.transcription import build_whisper_model


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
    build_whisper_model(
        settings.whisper_model,
        device=settings.whisper_device,
        device_index=settings.whisper_device_index,
        compute_type=settings.whisper_compute_type,
    )
    print("Whisper model is available.")


def main() -> None:
    download_configured_models(AppSettings())


if __name__ == "__main__":
    main()
