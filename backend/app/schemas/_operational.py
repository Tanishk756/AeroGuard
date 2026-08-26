"""Shared strict validation for Stage F1 data contracts."""

import json
from collections.abc import Mapping
from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, field_validator

MAX_METADATA_BYTES = 16_384
MAX_METADATA_DEPTH = 6
MAX_COLLECTION_ITEMS = 100
MAX_STRING_LENGTH = 512


def validate_metadata(value: Any) -> dict:
    if not isinstance(value, Mapping):
        raise ValueError("metadata must be an object")

    def validate(item: Any, depth: int) -> Any:
        if depth > MAX_METADATA_DEPTH:
            raise ValueError("metadata nesting is too deep")
        if isinstance(item, Mapping):
            if len(item) > MAX_COLLECTION_ITEMS:
                raise ValueError("metadata collection is too large")
            result = {}
            for key, child in item.items():
                key_text = str(key)
                if len(key_text) > MAX_STRING_LENGTH:
                    raise ValueError("metadata key is too long")
                result[key_text] = validate(child, depth + 1)
            return result
        if isinstance(item, (list, tuple)):
            if len(item) > MAX_COLLECTION_ITEMS:
                raise ValueError("metadata collection is too large")
            return [validate(child, depth + 1) for child in item]
        if item is None or isinstance(item, (bool, int, float)):
            return item
        if isinstance(item, str) and len(item) <= MAX_STRING_LENGTH:
            return item
        raise ValueError("metadata contains an unsupported or oversized value")

    result = validate(value, 0)
    if len(json.dumps(result, separators=(",", ":"), allow_nan=False).encode("utf-8")) > MAX_METADATA_BYTES:
        raise ValueError("metadata is too large")
    return result


def validate_utc(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("timestamp must be timezone-aware UTC")
    return value


class OperationalSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    @field_validator("metadata", "configuration_metadata", "factors", mode="after", check_fields=False)
    @classmethod
    def validate_json_metadata(cls, value: Any) -> dict:
        return validate_metadata(value)