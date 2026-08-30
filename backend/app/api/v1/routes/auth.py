"""Authentication and current-user endpoints."""

from fastapi import APIRouter, Depends, Request, Response
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.database.session import get_db
from app.dependencies import get_auth_context, get_current_user
from app.models.session import Session as AuthSession
from app.models.user import User
from app.schemas.auth import AuthenticationResponse, LoginRequest, LogoutResponse, PublicUser
from app.services.auth import create_session, revoke_session, verify_credentials
from app.services.audit import AuditService

from app.core.ip import get_client_ip
from app.core.rate_limiter import get_rate_limiter
from app.middleware.csrf import generate_csrf_token

router = APIRouter()


@router.post("/auth/login", response_model=AuthenticationResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    client_ip = get_client_ip(request, settings)
    limiter = get_rate_limiter()

    # Enforce login rate limits across IP and normalized username dimensions
    norm_identifier = payload.identifier.strip().casefold()
    try:
        limiter.enforce_rate_limit(request, f"login_ip:{client_ip}", settings.rate_limit_login, is_login=True)
        limiter.enforce_rate_limit(request, f"login_user:{norm_identifier}", settings.rate_limit_login, is_login=True)
    except Exception as exc:
        try:
            AuditService(db).record_event(
                "RATE_LIMIT_TRIGGERED",
                "login_rate_limit",
                "FAILURE",
                correlation=getattr(request.state, "correlation_id", None),
                source_ip=client_ip,
                user_agent=request.headers.get("user-agent"),
                metadata={"identifier": payload.identifier},
            )
            db.commit()
        except Exception:
            db.rollback()
        raise exc

    try:
        user = verify_credentials(db, payload.identifier, payload.password, settings=settings)
    except Exception:
        db.rollback()
        try:
            AuditService(db).record_event(
                "LOGIN_FAILURE",
                "authenticate",
                "FAILURE",
                correlation=getattr(request.state, "correlation_id", None),
                source_ip=client_ip,
                user_agent=request.headers.get("user-agent"),
                metadata={"identifier": payload.identifier},
            )
            db.commit()
        except Exception:
            db.rollback()
        raise

    session, raw_secret = create_session(db, user, client_ip, request.headers.get("user-agent"), settings, commit=False)
    AuditService(db).record_event("SESSION_CREATED", "create_session", "SUCCESS", correlation=getattr(request.state, "correlation_id", None), actor=user, session=session, source_ip=client_ip, user_agent=request.headers.get("user-agent"))
    AuditService(db).record_event("LOGIN_SUCCESS", "authenticate", "SUCCESS", correlation=getattr(request.state, "correlation_id", None), actor=user, session=session, source_ip=client_ip, user_agent=request.headers.get("user-agent"))
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise

    # Set session cookie
    response.set_cookie(
        key=settings.session_cookie_name,
        value=raw_secret,
        httponly=True,
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path=settings.session_cookie_path,
        domain=settings.session_cookie_domain,
        max_age=settings.session_lifetime_minutes * 60,
    )

    # Set CSRF cookie for double-submit token verification
    csrf_token = generate_csrf_token()
    response.set_cookie(
        key=settings.csrf_cookie_name,
        value=csrf_token,
        httponly=False,  # JavaScript readable to supply X-CSRF-Token header
        secure=settings.session_cookie_secure,
        samesite=settings.session_cookie_samesite,
        path=settings.session_cookie_path,
        domain=settings.session_cookie_domain,
    )

    return AuthenticationResponse(user=PublicUser.model_validate(user))


@router.post("/auth/logout", response_model=LogoutResponse)
def logout(
    request: Request,
    response: Response,
    context: tuple[AuthSession, User] = Depends(get_auth_context),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    revoke_session(db, context[0], commit=False)
    AuditService(db).record_event("LOGOUT", "logout", "SUCCESS", correlation=request.state.correlation_id, actor=context[1], session=context[0], source_ip=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
    AuditService(db).record_event("SESSION_REVOKED", "revoke_session", "SUCCESS", correlation=request.state.correlation_id, actor=context[1], session=context[0], source_ip=request.client.host if request.client else None, user_agent=request.headers.get("user-agent"))
    try:
        db.commit()
    except Exception:
        db.rollback()
        raise
    response.delete_cookie(key=settings.session_cookie_name, path=settings.session_cookie_path, domain=settings.session_cookie_domain)
    return LogoutResponse()


@router.get("/me", response_model=PublicUser)
def current_user(user: User = Depends(get_current_user)):
    return user