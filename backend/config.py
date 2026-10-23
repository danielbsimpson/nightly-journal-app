"""Application configuration loaded from the environment and ``.env``.

Field names mirror the variables documented in ``.env.example``; pydantic-settings
maps them case-insensitively (``whisper_model`` ← ``WHISPER_MODEL``).
"""

from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict

# The browser stops capture at 10 minutes; the backend treats its own measurement
# as authoritative and rejects anything longer. This is a hard ceiling, not config.
MAX_RECORDING_SECONDS: float = 600.0


class Settings(BaseSettings):
    """Runtime configuration for the backend."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # ─── Ollama ──────────────────────────────────────────────────────────
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "llama3"
    ollama_temperature: float = 0.5

    # ─── Whisper ─────────────────────────────────────────────────────────
    whisper_model: str = "base"
    whisper_device: str = "auto"
    whisper_language: str = "en"
    min_recording_seconds: float = 2.0

    # ─── Storage ─────────────────────────────────────────────────────────
    journals_dir: str = "./journals"
    retain_audio: bool = False

    # ─── Journaling ──────────────────────────────────────────────────────
    day_boundary_hour: int = 4

    # ─── Backend ─────────────────────────────────────────────────────────
    backend_host: str = "127.0.0.1"
    backend_port: int = 8000


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, loaded once."""

    return Settings()
