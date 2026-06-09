"""Application settings loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    secret_key: str = "please-change-this-to-a-long-random-string"
    database_url: str = "sqlite+aiosqlite:///./data/osint_hub.db"
    reports_dir: str = "./data/reports"

    sherlock_timeout: int = 180
    maigret_timeout: int = 240
    site_timeout: int = 15

    session_max_age: int = 60 * 60 * 24 * 7
    log_level: str = "INFO"


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
