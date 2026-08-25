"""Argon2id password hashing and policy validation."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError, VerifyMismatchError

from app.core.config import Settings, get_settings

_password_hasher = PasswordHasher()


def validate_password(password: str, settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if not settings.password_min_length <= len(password) <= settings.password_max_length:
        raise ValueError("Password does not meet the configured length requirements")


def hash_password(password: str, settings: Settings | None = None) -> str:
    validate_password(password, settings)
    return _password_hasher.hash(password)


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except (InvalidHashError, VerificationError, VerifyMismatchError):
        return False