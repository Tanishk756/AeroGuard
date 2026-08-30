"""Stage PR1-B SchedulerLock ORM Model."""

from datetime import datetime

from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from app.database.base import Base


class SchedulerLock(Base):
    """Distributed job lock and status tracking table for multi-worker coordination."""

    __tablename__ = "scheduler_locks"

    job_name: Mapped[str] = mapped_column(String(64), primary_key=True)
    locked_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    locked_at: Mapped[datetime | None] = mapped_column(nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_run_at: Mapped[datetime | None] = mapped_column(nullable=True)
    last_status: Mapped[str | None] = mapped_column(String(32), nullable=True)
    last_duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    records_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    retry_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
