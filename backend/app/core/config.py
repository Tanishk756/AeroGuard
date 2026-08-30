"""Typed application configuration loaded from environment variables."""

from functools import lru_cache

from typing import Literal

from pydantic import Field, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    application_name: str = "AeroGuard"
    environment: str = "development"
    debug: bool = False
    database_url: str = Field(default="sqlite:///./aeroguard.db", validation_alias="AEROGUARD_DATABASE_URL")
    db_pool_size: int = Field(default=10, ge=1, le=100, validation_alias="AEROGUARD_DB_POOL_SIZE")
    db_max_overflow: int = Field(default=20, ge=0, le=100, validation_alias="AEROGUARD_DB_MAX_OVERFLOW")
    db_pool_timeout: float = Field(default=30.0, ge=1.0, le=300.0, validation_alias="AEROGUARD_DB_POOL_TIMEOUT")
    db_pool_recycle: int = Field(default=1800, ge=60, le=7200, validation_alias="AEROGUARD_DB_POOL_RECYCLE")
    db_pool_pre_ping: bool = Field(default=True, validation_alias="AEROGUARD_DB_POOL_PRE_PING")
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

    # S3 / MinIO / S3-Compatible Cold Storage Configuration (IM3-A)
    s3_endpoint_url: str | None = Field(default=None, validation_alias="AEROGUARD_S3_ENDPOINT")
    s3_region: str = Field(default="us-east-1", validation_alias="AEROGUARD_S3_REGION")
    s3_bucket: str = Field(default="aeroguard-archives", validation_alias="AEROGUARD_S3_BUCKET")
    s3_access_key_id: str | None = Field(default=None, validation_alias="AEROGUARD_S3_ACCESS_KEY")
    s3_secret_access_key: str | None = Field(default=None, validation_alias="AEROGUARD_S3_SECRET_KEY")
    s3_sse_algorithm: str = Field(default="AES256", validation_alias="AEROGUARD_S3_SSE_ALGORITHM")
    s3_sse_kms_key_id: str | None = Field(default=None, validation_alias="AEROGUARD_S3_SSE_KMS_KEY_ID")
    retention_storage_provider: Literal["LOCAL", "S3"] = Field(default="LOCAL", validation_alias="AEROGUARD_RETENTION_STORAGE_PROVIDER")

    # Automated Operational Scheduler Settings (PR1-B)
    scheduler_enabled: bool = Field(default=True, validation_alias="AEROGUARD_SCHEDULER_ENABLED")
    retention_job_interval_seconds: int = Field(default=3600, ge=5, le=86400, validation_alias="AEROGUARD_RETENTION_JOB_INTERVAL_SECONDS")
    integrity_job_interval_seconds: int = Field(default=1800, ge=5, le=86400, validation_alias="AEROGUARD_INTEGRITY_JOB_INTERVAL_SECONDS")
    session_cleanup_interval_seconds: int = Field(default=7200, ge=5, le=86400, validation_alias="AEROGUARD_SESSION_CLEANUP_INTERVAL_SECONDS")
    session_cleanup_grace_period_days: int = Field(default=7, ge=1, le=90, validation_alias="AEROGUARD_SESSION_CLEANUP_GRACE_PERIOD_DAYS")
    scheduler_lock_timeout_seconds: int = Field(default=300, ge=10, le=3600, validation_alias="AEROGUARD_SCHEDULER_LOCK_TIMEOUT_SECONDS")

    # API Security, Rate Limiting & Account Lockout Settings (PR1-C)
    rate_limiting_enabled: bool = Field(default=True, validation_alias="AEROGUARD_RATE_LIMITING_ENABLED")
    rate_limit_login: str = Field(default="5/minute", validation_alias="AEROGUARD_RATE_LIMIT_LOGIN")
    rate_limit_default: str = Field(default="100/minute", validation_alias="AEROGUARD_RATE_LIMIT_DEFAULT")
    rate_limit_storage_url: str | None = Field(default=None, validation_alias="AEROGUARD_RATE_LIMIT_STORAGE_URL")
    rate_limit_fail_open: bool = Field(default=False, validation_alias="AEROGUARD_RATE_LIMIT_FAIL_OPEN")
    trusted_proxies: list[str] = Field(default_factory=list, validation_alias="AEROGUARD_TRUSTED_PROXIES")
    login_max_failed_attempts: int = Field(default=5, ge=1, le=20, validation_alias="AEROGUARD_LOGIN_MAX_FAILED_ATTEMPTS")
    login_lockout_duration_minutes: int = Field(default=15, ge=1, le=1440, validation_alias="AEROGUARD_LOGIN_LOCKOUT_DURATION_MINUTES")
    csrf_protection_enabled: bool = Field(default=True, validation_alias="AEROGUARD_CSRF_PROTECTION_ENABLED")
    csrf_cookie_name: str = Field(default="aeroguard_csrf", validation_alias="AEROGUARD_CSRF_COOKIE_NAME")
    security_headers_enabled: bool = Field(default=True, validation_alias="AEROGUARD_SECURITY_HEADERS_ENABLED")

    @field_validator("session_cookie_name")
    @classmethod
    def validate_cookie_name(cls, value: str) -> str:
        if not value or any(character.isspace() for character in value):
            raise ValueError("session_cookie_name must be non-empty and contain no whitespace")
        return value

    @field_validator("database_url")
    @classmethod
    def validate_database_url(cls, value: str) -> str:
        clean_url = value.strip()
        if not clean_url:
            raise ValueError("database_url must not be empty")
        valid_schemes = ("sqlite://", "sqlite+pysqlite://", "postgresql://", "postgresql+psycopg2://", "postgres://")
        if not any(clean_url.startswith(scheme) for scheme in valid_schemes):
            raise ValueError(f"Unsupported database scheme in URL: '{clean_url[:15]}...'. Supported dialects: SQLite and PostgreSQL.")
        return clean_url

    @field_validator("db_pool_size")
    @classmethod
    def validate_pool_size(cls, value: int) -> int:
        if value < 1 or value > 100:
            raise ValueError("db_pool_size must be between 1 and 100")
        return value

    @field_validator("db_max_overflow")
    @classmethod
    def validate_max_overflow(cls, value: int) -> int:
        if value < 0 or value > 100:
            raise ValueError("db_max_overflow must be between 0 and 100")
        return value

    @field_validator("db_pool_timeout")
    @classmethod
    def validate_pool_timeout(cls, value: float) -> float:
        if value <= 0 or value > 300.0:
            raise ValueError("db_pool_timeout must be greater than 0 and at most 300 seconds")
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
        populate_by_name=True,
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()