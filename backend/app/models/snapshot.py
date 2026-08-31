"""Stage S5 Simulation Run Snapshot & Traceability ORM Model."""

import uuid
from datetime import datetime, timezone
from sqlalchemy import Column, String, DateTime, JSON, ForeignKey
from sqlalchemy.orm import relationship

from app.database.base import Base


class PersistentSimulationRunSnapshot(Base):
    """Immutable snapshot entity created when a simulation run is initiated."""

    __tablename__ = "simulation_snapshots"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    run_id = Column(String(64), nullable=False, index=True)
    vehicle_id = Column(String(36), ForeignKey("vehicles.id"), nullable=False)
    compiled_model_hash = Column(String(64), nullable=False)
    artifact_hash = Column(String(64), nullable=False)
    provenance_json = Column(JSON, nullable=False)
    compiled_metadata_json = Column(JSON, nullable=False)
    created_at = Column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)

    vehicle = relationship("PersistentVehicle")
