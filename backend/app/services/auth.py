"""Authentication and server-side session operations."""

import hashlib
import hmac
import logging
import secrets
from datetime import UTC, datetime, timedelta

logger = logging.getLogger(__name__)

from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AuthError
from app.models.session import Session as AuthSession
from app.models.user import User, UserStatus
from app.services.passwords import hash_password, verify_password

INVALID_CREDENTIALS = "AUTH_INVALID_CREDENTIALS"


def normalize_username(value: str) -> str:
    return value.strip().casefold()


def normalize_email(value: str) -> str:
    return value.strip().casefold()


def create_user(db: Session, username: str, display_name: str, email: str, password: str) -> User:
    user = User(
        username=normalize_username(username),
        display_name=display_name.strip(),
        email=normalize_email(email),
        password_hash=hash_password(password),
        status=UserStatus.ACTIVE,
    )
    db.add(user)
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise ValueError("Username or email is already in use") from exc
    db.refresh(user)
    return user


def _find_user(db: Session, identifier: str) -> User | None:
    normalized = identifier.strip().casefold()
    return db.scalar(select(User).where(or_(User.username == normalized, User.email == normalized)))


def verify_credentials(db: Session, identifier: str, password: str, settings: Settings | None = None) -> User:
    """Verify user login credentials with account lockout protection and user enumeration resistance."""
    if settings is None:
        settings = get_settings()

    now = datetime.now(UTC).replace(tzinfo=None)
    user = _find_user(db, identifier)

    if user is None:
        # Uniform authentication response for invalid user / password (no user enumeration)
        raise AuthError(INVALID_CREDENTIALS, "Invalid username or password.")

    # 1. Active Account Lockout Check
    if user.locked_until is not None:
        if user.locked_until > now:
            logger.warning(f"[AUTH_SECURITY] Login attempt for locked user '{user.id}' rejected.")
            raise AuthError(INVALID_CREDENTIALS, "Invalid username or password.")
        else:
            # Lockout period has expired - clear expired lock state
            user.locked_until = None

    # 2. Verify Password
    valid = verify_password(password, user.password_hash)

    if not valid or user.status != UserStatus.ACTIVE:
        # Increment failed login attempts atomically
        user.failed_login_attempts += 1
        if user.failed_login_attempts >= settings.login_max_failed_attempts:
            user.locked_until = now + timedelta(minutes=settings.login_lockout_duration_minutes)
            logger.warning(
                f"[AUTH_SECURITY] Account '{user.id}' locked for {settings.login_lockout_duration_minutes}m "
                f"after {user.failed_login_attempts} failed login attempts."
            )
        try:
            db.commit()
        except Exception:
            db.rollback()

        raise AuthError(INVALID_CREDENTIALS, "Invalid username or password.")

    # 3. Successful Authentication - Clear failed counters and set last login timestamp
    user.failed_login_attempts = 0
    user.locked_until = None
    user.last_login_at = now
    try:
        db.commit()
    except Exception:
        db.rollback()

    return user


def hash_session_secret(secret: str) -> str:
    return hashlib.sha256(secret.encode("utf-8")).hexdigest()


def create_session(
    db: Session,
    user: User,
    client_ip: str | None,
    user_agent: str | None,
    settings: Settings | None = None,
    *,
    commit: bool = True,
) -> tuple[AuthSession, str]:
    settings = settings or get_settings()
    raw_secret = secrets.token_urlsafe(48)
    now = datetime.now(UTC).replace(tzinfo=None)
    session = AuthSession(
        user_id=user.id,
        session_secret_hash=hash_session_secret(raw_secret),
        created_at=now,
        expires_at=now + timedelta(minutes=settings.session_lifetime_minutes),
        last_seen_at=now,
        client_ip=client_ip[:45] if client_ip else None,
        user_agent=user_agent[:512] if user_agent else None,
    )
    user.last_login_at = now
    db.add(session)
    db.flush()
    if commit:
        db.commit()
        db.refresh(session)
    return session, raw_secret


def resolve_session(db: Session, raw_secret: str) -> tuple[AuthSession, User] | None:
    if not raw_secret or len(raw_secret) > 256:
        return None
    session = db.scalar(select(AuthSession).where(AuthSession.session_secret_hash == hash_session_secret(raw_secret)))
    if session is None or not hmac.compare_digest(session.session_secret_hash, hash_session_secret(raw_secret)):
        return None
    user = session.user
    if session.revoked_at is not None or session.expires_at <= datetime.now(UTC).replace(tzinfo=None) or user.status != UserStatus.ACTIVE:
        return None
    session.last_seen_at = datetime.now(UTC).replace(tzinfo=None)
    db.commit()
    return session, user


def revoke_session(db: Session, session: AuthSession, *, commit: bool = True) -> None:
    if session.revoked_at is None:
        session.revoked_at = datetime.now(UTC).replace(tzinfo=None)
        if commit:
            db.commit()