"""Reusable authentication dependencies."""

from datetime import UTC, datetime

from fastapi import Depends, Request
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.errors import AuthError
from app.database.session import get_db
from app.models.session import Session as AuthSession
from app.models.user import User
from app.services.auth import hash_session_secret
from app.services.authorization import AuthorizationService
from app.services.audit import AuditService


def get_auth_context(
    request: Request,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
) -> tuple[AuthSession, User]:
    session_secret = request.cookies.get(settings.session_cookie_name)
    if not session_secret:
        raise AuthError("AUTH_UNAUTHENTICATED", "Authentication is required.")
    try:
        session = db.scalar(select(AuthSession).where(AuthSession.session_secret_hash == hash_session_secret(session_secret)))
        if session is None:
            raise AuthError("AUTH_UNAUTHENTICATED", "Authentication is required.")
        if session.revoked_at is not None:
            raise AuthError("AUTH_SESSION_REVOKED", "The session is no longer valid.")
        if session.expires_at <= datetime.now(UTC).replace(tzinfo=None):
            try:
                AuditService(db).record_event("SESSION_EXPIRED", "resolve_session", "FAILURE", correlation=getattr(request.state, "correlation_id", None), actor=session.user, session=session, source_ip=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
                db.commit()
            except Exception:
                db.rollback()
            raise AuthError("AUTH_SESSION_EXPIRED", "The session has expired.")
        user = session.user
        if user.status.value == "DISABLED":
            raise AuthError("AUTH_USER_DISABLED", "The user account is disabled.")
        session.last_seen_at = datetime.now(UTC).replace(tzinfo=None)
        db.commit()
        return session, user
    except AuthError:
        raise
    except SQLAlchemyError as exc:
        db.rollback()
        raise AuthError("AUTH_UNAUTHENTICATED", "Authentication is required.") from exc


def get_current_user(context: tuple[AuthSession, User] = Depends(get_auth_context)) -> User:
    return context[1]


def require_permission(permission_key: str):
    def dependency(
        request: Request,
        context = Depends(get_auth_context),
        db: Session = Depends(get_db),
    ) -> User:
        if isinstance(request, User) and isinstance(context, Session):
            user, db, session = request, context, None
            request = None
        else:
            session, user = context
        if not AuthorizationService(db).has_permission(user, permission_key):
            try:
                AuditService(db).record_event("AUTHORIZATION_DENIED", "authorize", "DENIED", correlation=getattr(request.state, "correlation_id", None) if request else None, actor=user, session=session, permission=permission_key, target_type="endpoint", target_id=request.url.path if request else None, source_ip=request.client.host if request and request.client else None, user_agent=request.headers.get("user-agent") if request else None, metadata={"method": request.method} if request else {})
                db.commit()
            except Exception:
                db.rollback()
            raise AuthError("AUTH_FORBIDDEN", "You do not have permission to perform this action.", 403)
        return user

    return dependency


def require_any_permission(*permission_keys: str):
    if not permission_keys:
        raise ValueError("At least one permission is required")

    def dependency(request: Request, context = Depends(get_auth_context), db: Session = Depends(get_db)) -> User:
        if isinstance(request, User) and isinstance(context, Session):
            user, db, session = request, context, None
            request = None
        else:
            session, user = context
        if not AuthorizationService(db).has_any_permission(user, permission_keys):
            try:
                AuditService(db).record_event("AUTHORIZATION_DENIED", "authorize", "DENIED", correlation=getattr(request.state, "correlation_id", None) if request else None, actor=user, session=session, permission=",".join(permission_keys), target_type="endpoint", target_id=request.url.path if request else None, source_ip=request.client.host if request and request.client else None, user_agent=request.headers.get("user-agent") if request else None)
                db.commit()
            except Exception:
                db.rollback()
            raise AuthError("AUTH_FORBIDDEN", "You do not have permission to perform this action.", 403)
        return user

    return dependency


def require_all_permissions(*permission_keys: str):
    if not permission_keys:
        raise ValueError("At least one permission is required")

    def dependency(request: Request, context = Depends(get_auth_context), db: Session = Depends(get_db)) -> User:
        if isinstance(request, User) and isinstance(context, Session):
            user, db, session = request, context, None
            request = None
        else:
            session, user = context
        if not AuthorizationService(db).has_all_permissions(user, permission_keys):
            try:
                AuditService(db).record_event("AUTHORIZATION_DENIED", "authorize", "DENIED", correlation=getattr(request.state, "correlation_id", None) if request else None, actor=user, session=session, permission=",".join(permission_keys), target_type="endpoint", target_id=request.url.path if request else None, source_ip=request.client.host if request and request.client else None, user_agent=request.headers.get("user-agent") if request else None)
                db.commit()
            except Exception:
                db.rollback()
            raise AuthError("AUTH_FORBIDDEN", "You do not have permission to perform this action.", 403)
        return user

    return dependency