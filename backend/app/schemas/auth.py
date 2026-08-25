"""Authentication request and public response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.models.user import UserStatus


class LoginRequest(BaseModel):
    identifier: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=256)


class PublicUser(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    username: str
    display_name: str
    email: str
    status: UserStatus
    created_at: datetime
    updated_at: datetime
    last_login_at: datetime | None


class AuthenticationResponse(BaseModel):
    authenticated: bool = True
    user: PublicUser


class LogoutResponse(BaseModel):
    authenticated: bool = False