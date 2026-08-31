"""SQLAlchemy database models for simulation scenarios, runs, and telemetry recordings."""

from datetime import datetime
from typing import Any, Dict
from sqlalchemy import JSON, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class PersistentSimulationScenario(Base):
    __tablename__ = "simulation_scenarios"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    configuration_version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    configuration_metadata: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    runs: Mapped[list["PersistentSimulationRun"]] = relationship(
        "PersistentSimulationRun", back_populates="scenario", cascade="all, delete-orphan"
    )


class PersistentSimulationRun(Base):
    __tablename__ = "simulation_runs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    scenario_id: Mapped[str] = mapped_column(String(64), ForeignKey("simulation_scenarios.id", ondelete="CASCADE"), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="CREATED", nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    stopped_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    telemetry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    artifact_path: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    scenario: Mapped["PersistentSimulationScenario"] = relationship(
        "PersistentSimulationScenario", back_populates="runs"
    )
