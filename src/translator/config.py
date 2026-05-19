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
