"""RBAC request and response schemas."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class PermissionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    key: str
    resource: str
    action: str
    description: str


class RoleCreate(BaseModel):
    name: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z][A-Z0-9_]+$")
    description: str = Field(min_length=1, max_length=300)


class RoleUpdate(BaseModel):
    description: str = Field(min_length=1, max_length=300)


class RoleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    description: str
    is_system: bool
    created_at: datetime
    updated_at: datetime
    permissions: list[PermissionResponse] = Field(default_factory=list)


class RoleAssignmentResponse(BaseModel):
    user_id: str
    role_id: str
    role_name: str
