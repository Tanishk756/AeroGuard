"""Application-validated geofence configuration model."""

from datetime import UTC, datetime
from uuid import uuid4

from sqlalchemy import Boolean, CheckConstraint, DateTime, Index, JSON, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class Geofence(Base):
    __tablename__ = "geofences"
    __table_args__ = (
        CheckConstraint("length(name) between 1 and 200", name="ck_geofences_name_length"),
        CheckConstraint("min_altitude is null or max_altitude is null or min_altitude <= max_altitude", name="ck_geofences_altitude_range"),
        Index("ix_geofences_enabled", "enabled"),
    )

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    geometry: Mapped[dict] = mapped_column(JSON, nullable=False)
    min_altitude: Mapped[float | None] = mapped_column(nullable=True)
    max_altitude: Mapped[float | None] = mapped_column(nullable=True)
    metadata_json: Mapped[dict] = mapped_column("metadata", JSON, nullable=False, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None))
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=lambda: datetime.now(UTC).replace(tzinfo=None), onupdate=lambda: datetime.now(UTC).replace(tzinfo=None))


def _get_metadata(geofence: Geofence) -> dict:
    return geofence.metadata_json


def _set_metadata(geofence: Geofence, value: dict) -> None:
    geofence.metadata_json = value


Geofence.metadata = property(_get_metadata, _set_metadata)