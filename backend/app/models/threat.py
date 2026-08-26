"""Stored, informational threat prioritization assessment."""

from datetime import UTC, datetime
from enum import StrEnum
from uuid import uuid4

from sqlalchemy import CheckConstraint, DateTime, Enum, ForeignKey, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class ThreatLevel(StrEnum):
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"
    CRITICAL = "CRITICAL"


class ThreatAssessment(Base):
    __tablename__ = "threat_assessments"
    __table_args__ = (
        UniqueConstraint("track_id", name="uq_threat_assessments_track_id"),
        CheckConstraint("score between 0 and 100", name="ck_threat_assessments_score"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    track_id: Mapped[str] = mapped_column(ForeignKey("tracks.id", ondelete="CASCADE"), nullable=False)
    score: Mapped[float] = mapped_column(nullable=False)
    level: Mapped[ThreatLevel] = mapped_column(Enum(ThreatLevel, native_enum=False, create_constraint=True), nullable=False)
    factors: Mapped[dict] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None))

    track = relationship("Track", back_populates="threat_assessments")