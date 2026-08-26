"""Geofence data contracts with application-level geometry validation and response schemas."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, FiniteFloat, field_validator

from app.schemas._operational import OperationalSchema


class GeofenceSchema(OperationalSchema):
    id: str | None = None
    name: str = Field(min_length=1, max_length=200)
    enabled: bool = True
    geometry: dict[str, Any]
    min_altitude: FiniteFloat | None = Field(default=None, ge=0)
    max_altitude: FiniteFloat | None = Field(default=None, ge=0)
    metadata: dict = Field(default_factory=dict)
    created_at: datetime | None = None
    updated_at: datetime | None = None

    @field_validator("geometry")
    @classmethod
    def validate_geometry(cls, value: dict[str, Any]) -> dict[str, Any]:
        geometry_type = value.get("type")
        if geometry_type == "bbox":
            required = {"min_lat", "min_lon", "max_lat", "max_lon"}
            if set(value) != required:
                raise ValueError("bbox geometry must contain exactly four bounds")
            if not (-90 <= value["min_lat"] <= value["max_lat"] <= 90 and -180 <= value["min_lon"] <= value["max_lon"] <= 180):
                raise ValueError("bbox coordinates are invalid")
        elif geometry_type == "polygon":
            coordinates = value.get("coordinates")
            if not isinstance(coordinates, list) or len(coordinates) < 3:
                raise ValueError("polygon requires at least three points")
            for point in coordinates:
                if not isinstance(point, list) or len(point) != 2 or not all(isinstance(number, (int, float)) and not isinstance(number, bool) for number in point):
                    raise ValueError("polygon points must be latitude/longitude pairs")
                if not (-90 <= point[0] <= 90 and -180 <= point[1] <= 180):
                    raise ValueError("polygon coordinates are invalid")
        else:
            raise ValueError("geometry type must be bbox or polygon")
        return value


class GeofenceResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    name: str
    enabled: bool
    geometry: dict[str, Any]
    min_altitude: float | None = None
    max_altitude: float | None = None
    metadata: dict = Field(alias="metadata_json")
    created_at: datetime
    updated_at: datetime


class GeofencePage(BaseModel):
    items: list[GeofenceResponse]
    next_cursor: str | None = None