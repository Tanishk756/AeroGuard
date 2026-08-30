"""Structured JSON logging setup and centralized secret redaction filter."""

from datetime import UTC, datetime
import json
import logging
import re
from typing import Any

SECRET_KEYS_REGEX = re.compile(
    r"(password|secret|api_key|access_key|token|bearer|cookie|authorization|s3_secret)",
    re.IGNORECASE,
)
SENSITIVE_PATTERN_REGEX = re.compile(
    r"(?:password|secret|api_key|token|access_key|bearer|cookie)=['\"]?[^'\";\s]+['\"]?",
    re.IGNORECASE,
)


def redact_data(data: Any) -> Any:
    """Recursively sanitize sensitive values from dictionaries, lists, and text strings."""
    if isinstance(data, dict):
        sanitized = {}
        for key, val in data.items():
            if SECRET_KEYS_REGEX.search(str(key)):
                sanitized[key] = "[REDACTED]"
            else:
                sanitized[key] = redact_data(val)
        return sanitized
    elif isinstance(data, list):
        return [redact_data(item) for item in data]
    elif isinstance(data, str):
        return SENSITIVE_PATTERN_REGEX.sub("[REDACTED]", data)
    return data


class RedactingFilter(logging.Filter):
    """Logging filter replacing sensitive values in record messages and arguments with [REDACTED]."""

    def filter(self, record: logging.LogRecord) -> bool:
        if isinstance(record.msg, str):
            record.msg = redact_data(record.msg)
        if isinstance(record.args, dict):
            record.args = redact_data(record.args)
        elif isinstance(record.args, (list, tuple)):
            record.args = tuple(redact_data(item) for item in record.args)
        return True


class JSONFormatter(logging.Formatter):
    """Production-grade structured JSON log formatter."""

    def format(self, record: logging.LogRecord) -> str:
        log_entry = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": redact_data(record.getMessage()),
        }

        # Attach request context if available
        request_id = getattr(record, "request_id", None) or getattr(record, "correlation_id", None)
        if request_id:
            log_entry["request_id"] = str(request_id)

        method = getattr(record, "method", None)
        if method:
            log_entry["method"] = str(method)

        route = getattr(record, "route", None)
        if route:
            log_entry["route"] = str(route)

        status_code = getattr(record, "status_code", None)
        if status_code is not None:
            log_entry["status_code"] = int(status_code)

        duration_ms = getattr(record, "duration_ms", None)
        if duration_ms is not None:
            log_entry["duration_ms"] = float(duration_ms)

        if record.exc_info:
            log_entry["exception"] = self.formatException(record.exc_info)

        return json.dumps(log_entry)


def configure_logging(log_level: str = "INFO", json_format: bool = True) -> None:
    """Configure application logging with structured JSON formatting and secret redaction."""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers
    root_logger.handlers.clear()

    handler = logging.StreamHandler()
    handler.setLevel(numeric_level)
    handler.addFilter(RedactingFilter())

    if json_format:
        handler.setFormatter(JSONFormatter())
    else:
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(name)s %(message)s"))

    root_logger.addHandler(handler)