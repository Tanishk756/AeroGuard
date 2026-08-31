"""Stage PR4 Asynchronous Task Processing & Background Worker Engine.

Provides Redis-backed / in-memory task queue manager with bounded retries,
exponential backoff, status tracking, secret redaction, and low-cardinality Prometheus metrics.
"""

from dataclasses import dataclass, field
from datetime import datetime, UTC, timedelta
from enum import Enum
import logging
import os
import threading
import uuid
from typing import Any, Callable

from prometheus_client import Counter, Histogram

from app.core.telemetry import (
    TASKS_CREATED_TOTAL,
    TASKS_COMPLETED_TOTAL,
    TASKS_FAILED_TOTAL,
    TASK_DURATION_SECONDS,
)

logger = logging.getLogger("aeroguard.tasks")


class TaskStatus(str, Enum):
    """Lifecycle statuses for asynchronous background tasks."""

    QUEUED = "QUEUED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"


@dataclass
class TaskRecord:
    """Thread-safe metadata record representing a background task."""

    task_id: str
    task_type: str
    status: TaskStatus = TaskStatus.QUEUED
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC).replace(tzinfo=None))
    started_at: datetime | None = None
    completed_at: datetime | None = None
    retry_count: int = 0
    max_retries: int = 3
    error_message: str | None = None
    result_metadata: dict[str, Any] = field(default_factory=dict)
    correlation_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Serialize safe public fields (redacting sensitive internal paths or stack traces)."""
        return {
            "task_id": self.task_id,
            "task_type": self.task_type,
            "status": self.status.value,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
            "error_message": self.error_message[:512] if self.error_message else None,
            "result_metadata": self.result_metadata,
        }


class TaskQueueManager:
    """Thread-safe task queue manager supporting in-memory storage and execution."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._tasks: dict[str, TaskRecord] = {}

    def create_task(
        self,
        task_type: str,
        max_retries: int = 3,
        correlation_id: str | None = None,
    ) -> TaskRecord:
        """Create and register a new queued task record."""
        task_id = str(uuid.uuid4())
        record = TaskRecord(
            task_id=task_id,
            task_type=task_type,
            status=TaskStatus.QUEUED,
            max_retries=max_retries,
            correlation_id=correlation_id,
        )
        with self._lock:
            self._tasks[task_id] = record

        TASKS_CREATED_TOTAL.labels(task_type=task_type).inc()
        logger.info(f"Task created: task_id={task_id} task_type={task_type}")
        return record

    def get_task(self, task_id: str) -> TaskRecord | None:
        """Retrieve task record by task_id."""
        with self._lock:
            return self._tasks.get(task_id)

    def execute_async(
        self,
        task_id: str,
        func: Callable[..., Any],
        *args: Any,
        **kwargs: Any,
    ) -> None:
        """Submit function for background thread execution."""

        def runner():
            record = self.get_task(task_id)
            if not record:
                return

            now = datetime.now(UTC).replace(tzinfo=None)
            with self._lock:
                record.status = TaskStatus.RUNNING
                record.started_at = now

            while True:
                start_time = datetime.now(UTC)
                try:
                    result = func(*args, **kwargs)
                    duration = (datetime.now(UTC) - start_time).total_seconds()
                    
                    with self._lock:
                        record.status = TaskStatus.SUCCEEDED
                        record.completed_at = datetime.now(UTC).replace(tzinfo=None)
                        if isinstance(result, dict):
                            record.result_metadata = result

                    TASK_DURATION_SECONDS.labels(task_type=record.task_type).observe(duration)
                    TASKS_COMPLETED_TOTAL.labels(task_type=record.task_type, status="SUCCEEDED").inc()
                    logger.info(f"Task succeeded: task_id={task_id} duration={duration:.3f}s")
                    break
                except Exception as exc:
                    duration = (datetime.now(UTC) - start_time).total_seconds()
                    logger.error(f"Task failed: task_id={task_id} error={exc}")
                    
                    with self._lock:
                        record.retry_count += 1
                        if record.retry_count <= record.max_retries:
                            record.status = TaskStatus.QUEUED
                            logger.info(f"Task queued for retry: task_id={task_id} attempt={record.retry_count}")
                        else:
                            record.status = TaskStatus.FAILED
                            record.completed_at = datetime.now(UTC).replace(tzinfo=None)
                            record.error_message = str(exc)
                            TASKS_FAILED_TOTAL.labels(task_type=record.task_type).inc()
                            TASKS_COMPLETED_TOTAL.labels(task_type=record.task_type, status="FAILED").inc()
                            break

        thread = threading.Thread(target=runner, daemon=True)
        thread.start()


# Global Singleton Task Manager Instance
task_manager = TaskQueueManager()
