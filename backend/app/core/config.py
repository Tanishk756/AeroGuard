"""Typed application configuration loaded from environment variables."""

from functools import lru_cache

from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    application_name: str = "AeroGuard"
    environment: str = "development"
    debug: bool = False
    database_url: str = "sqlite:///./aeroguard.db"
    api_prefix: str = "/api/v1"
    log_level: str = "INFO"
    version: str = Field(default="0.1.0", validation_alias="AEROGUARD_VERSION")
    session_lifetime_minutes: int = Field(default=60, ge=5, le=1440)
    session_cookie_name: str = "aeroguard_session"
    session_cookie_path: str = "/api/v1"
    session_cookie_domain: str | None = None
    session_cookie_samesite: Literal["lax", "strict", "none"] = "lax"
    session_cookie_secure: bool = False
    allowed_origins: list[str] = Field(default_factory=lambda: ["http://localhost:5173", "http://127.0.0.1:5173"])
    csrf_protection_enabled: bool = True
    password_min_length: int = Field(default=12, ge=8, le=128)
    password_max_length: int = Field(default=128, ge=8, le=256)

    @field_validator("session_cookie_name")
    @classmethod
    def validate_cookie_name(cls, value: str) -> str:
        if not value or any(character.isspace() for character in value):
            raise ValueError("session_cookie_name must be non-empty and contain no whitespace")
        return value

    @model_validator(mode="after")
    def validate_security_settings(self) -> "Settings":
        if self.password_min_length > self.password_max_length:
            raise ValueError("password_min_length cannot exceed password_max_length")
        if self.session_cookie_samesite == "none" and not self.session_cookie_secure:
            raise ValueError("SameSite=None requires a secure session cookie")
        if self.environment.lower() not in {"development", "dev", "test", "testing"}:
            if not self.session_cookie_secure:
                raise ValueError("session_cookie_secure must be enabled outside local development")
            if not self.allowed_origins:
                raise ValueError("allowed_origins must be configured outside local development")
        return self

    model_config = SettingsConfigDict(
        env_prefix="AEROGUARD_",
        env_file=".env",
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()