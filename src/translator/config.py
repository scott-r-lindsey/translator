from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class AppSettings(BaseSettings):
    """Runtime settings for the subtitle shell."""

    model_config = SettingsConfigDict(env_prefix="TRANSLATOR_", extra="ignore")

    window_title: str = "Live Subtitles"
    placeholder_text: str = "Waiting for audio..."
    width: int = Field(default=640, ge=320, le=1920)
    height: int = Field(default=160, ge=100, le=1080)
    opacity: float = Field(default=0.9, ge=0.2, le=1.0)
    always_on_top: bool = True
    audio_source: str | None = None
    audio_sample_rate: int = Field(default=16_000, ge=8_000, le=48_000)
    audio_chunk_frames: int = Field(default=1_600, ge=400, le=8_000)
    audio_detection_threshold: float = Field(default=0.01, ge=0.0, le=1.0)
    speech_start_ms: int = Field(default=300, ge=100, le=5_000)
    speech_end_ms: int = Field(default=800, ge=100, le=5_000)
    speech_max_ms: int = Field(default=10_000, ge=1_000, le=60_000)
    speech_overlap_ms: int = Field(default=1_000, ge=0, le=5_000)
    vad_aggressiveness: int = Field(default=2, ge=0, le=3)
    vad_frame_ms: int = Field(default=30, ge=10, le=30)
    vad_speech_ratio: float = Field(default=0.5, ge=0.0, le=1.0)
    debug_audio_dir: str | None = None
