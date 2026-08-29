"""Incident export tracking and compliance metadata model."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class IncidentExportFormat(StrEnum):
    JSON = "JSON"
    CSV = "CSV"
    PDF = "PDF"


class IncidentExportStatus(StrEnum):
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class IncidentExport(Base):
    __tablename__ = "incident_exports"
    __table_args__ = (
        Index("ix_incident_exports_export_number", "export_number", unique=True),
        Index("ix_incident_exports_requested_by", "requested_by"),
        Index("ix_incident_exports_created_at", "created_at"),
        Index("ix_incident_exports_status", "status"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    export_number: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    requested_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    format: Mapped[IncidentExportFormat] = mapped_column(
        Enum(IncidentExportFormat, native_enum=False, create_constraint=True),
        nullable=False,
    )
    status: Mapped[IncidentExportStatus] = mapped_column(
        Enum(IncidentExportStatus, native_enum=False, create_constraint=True),
        nullable=False,
        default=IncidentExportStatus.PENDING,
    )
    record_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    file_size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    sha256_checksum: Mapped[str] = mapped_column(String(64), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None)
    )
    completed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    filter_params_json: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    payload_data: Mapped[str] = mapped_column(Text, nullable=False)

    user = relationship("User", foreign_keys=[requested_by])
