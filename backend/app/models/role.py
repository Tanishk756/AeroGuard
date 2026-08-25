"""RBAC role and association models."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, String, Table, Column, event, inspect
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base

user_roles = Table(
    "user_roles",
    Base.metadata,
    Column("user_id", String(36), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="RESTRICT"), primary_key=True),
    Index("ix_user_roles_role_id", "role_id"),
)

role_permissions = Table(
    "role_permissions",
    Base.metadata,
    Column("role_id", String(36), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True),
    Column("permission_id", String(36), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True),
    Index("ix_role_permissions_permission_id", "permission_id"),
)


class Role(Base):
    __tablename__ = "roles"
    __table_args__ = (Index("ix_roles_is_system", "is_system"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)

    users: Mapped[list["User"]] = relationship(secondary=user_roles, back_populates="roles")
    permissions: Mapped[list["Permission"]] = relationship(secondary=role_permissions, back_populates="roles")


@event.listens_for(Role, "before_insert")
def validate_role_insert(mapper, connection, target: Role) -> None:
    target.name = target.name.strip().upper()
    if target.name in {"SUPER_ADMIN", "SYSTEM_ADMIN", "SECURITY_ADMIN", "OPERATIONS_ADMIN", "OPERATOR", "ANALYST", "RESEARCHER", "VIEWER"}:
        if not target.is_system:
            raise ValueError("System role names are reserved")


@event.listens_for(Role, "before_update")
def protect_system_role(mapper, connection, target: Role) -> None:
    state = inspect(target)
    if target.is_system and (state.attrs.name.history.has_changes() or state.attrs.is_system.history.has_changes()):
        raise ValueError("System role identity is immutable")
    if not target.is_system and target.name in {"SUPER_ADMIN", "SYSTEM_ADMIN", "SECURITY_ADMIN", "OPERATIONS_ADMIN", "OPERATOR", "ANALYST", "RESEARCHER", "VIEWER"}:
        raise ValueError("System role names are reserved")