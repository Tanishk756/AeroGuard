"""Incident retention policy, archival lifecycle, and compliance hold domain models."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class IncidentArchivalState(StrEnum):
    ACTIVE = "ACTIVE"
    ARCHIVE_ELIGIBLE = "ARCHIVE_ELIGIBLE"
    ARCHIVE_PENDING = "ARCHIVE_PENDING"
    ARCHIVED = "ARCHIVED"
    ARCHIVE_FAILED = "ARCHIVE_FAILED"
    PURGE_ELIGIBLE = "PURGE_ELIGIBLE"
    PURGE_APPROVED = "PURGE_APPROVED"
    PURGED = "PURGED"


class IncidentRetentionPolicy(Base):
    __tablename__ = "incident_retention_policies"
    __table_args__ = (
        Index("ix_incident_retention_policies_enabled", "enabled"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    policy_name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    incident_retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=90)
    export_retention_days: Mapped[int] = mapped_column(Integer, nullable=False, default=180)
    minimum_archive_age_days: Mapped[int] = mapped_column(Integer, nullable=False, default=30)
    minimum_purge_age_days: Mapped[int] = mapped_column(Integer, nullable=False, default=180)
    require_archive_before_purge: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    require_supervisor_approval: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    dry_run_by_default: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None)
    )


class IncidentRetentionHold(Base):
    __tablename__ = "incident_retention_holds"
    __table_args__ = (
        Index("ix_incident_retention_holds_incident_id", "incident_id"),
        Index("ix_incident_retention_holds_active", "active"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    placed_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    placed_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    released_by: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    released_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    incident = relationship("Incident", foreign_keys=[incident_id])


class IncidentArchive(Base):
    __tablename__ = "incident_archives"
    __table_args__ = (
        Index("ix_incident_archives_archive_number", "archive_number", unique=True),
        Index("ix_incident_archives_incident_id", "incident_id"),
        Index("ix_incident_archives_archived_at", "archived_at"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    archive_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    incident_id: Mapped[str] = mapped_column(String(36), ForeignKey("incidents.id", ondelete="CASCADE"), nullable=False)
    policy_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("incident_retention_policies.id", ondelete="SET NULL"), nullable=True)
    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    archive_format: Mapped[str] = mapped_column(String(16), nullable=False, default="JSON")
    payload_data: Mapped[str] = mapped_column(Text, nullable=False)
    archived_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    archived_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    verified_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    storage_provider: Mapped[str] = mapped_column(String(32), nullable=False, default="LOCAL")
    storage_location: Mapped[str | None] = mapped_column(String(512), nullable=True)
    presigned_url_expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    incident = relationship("Incident", foreign_keys=[incident_id])
