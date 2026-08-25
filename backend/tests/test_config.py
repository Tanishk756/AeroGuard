"""Configuration validation tests."""

import pytest
from pydantic import ValidationError

from app.core.config import Settings


def test_configuration_defaults_are_safe():
    settings = Settings(_env_file=None)

    assert settings.application_name == "AeroGuard"
    assert settings.environment == "development"
    assert settings.debug is False
    assert settings.database_url == "sqlite:///./aeroguard.db"
    assert settings.api_prefix == "/api/v1"
    assert settings.log_level == "INFO"


def test_configuration_rejects_invalid_debug_value(monkeypatch):
    monkeypatch.setenv("AEROGUARD_DEBUG", "definitely-not-a-boolean")

    with pytest.raises(ValidationError):
        Settings(_env_file=None)