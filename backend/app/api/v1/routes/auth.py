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

router = APIRouter()


@router.post("/auth/login", response_model=AuthenticationResponse)
def login(
    payload: LoginRequest,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    user = verify_credentials(db, payload.identifier, payload.password)
    _, raw_secret = create_session(db, user, request.client.host if request.client else None, request.headers.get("user-agent"), settings)
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
    return AuthenticationResponse(user=PublicUser.model_validate(user))


@router.post("/auth/logout", response_model=LogoutResponse)
def logout(
    response: Response,
    context: tuple[AuthSession, User] = Depends(get_auth_context),
    db: Session = Depends(get_db),
    settings: Settings = Depends(get_settings),
):
    revoke_session(db, context[0])
    response.delete_cookie(key=settings.session_cookie_name, path=settings.session_cookie_path, domain=settings.session_cookie_domain)
    return LogoutResponse()


@router.get("/me", response_model=PublicUser)
def current_user(user: User = Depends(get_current_user)):
    return user