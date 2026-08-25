"""RBAC permission model."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import DateTime, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base
from app.models.role import role_permissions


class Permission(Base):
    __tablename__ = "permissions"
    __table_args__ = (Index("ix_permissions_resource", "resource"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    key: Mapped[str] = mapped_column(String(100), unique=True, index=True, nullable=False)
    resource: Mapped[str] = mapped_column(String(50), nullable=False)
    action: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(300), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(UTC).replace(tzinfo=None), nullable=False)

    roles: Mapped[list["Role"]] = relationship(secondary=role_permissions, back_populates="permissions")