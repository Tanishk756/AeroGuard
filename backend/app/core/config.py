"""Typed application configuration loaded from environment variables."""

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    application_name: str = "AeroGuard"
    environment: str = "development"
    debug: bool = False
    database_url: str = "sqlite:///./aeroguard.db"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    version: str = Field(default="0.1.0", validation_alias="AEROGUARD_VERSION")

    model_config = SettingsConfigDict(
        env_prefix="AEROGUARD_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()