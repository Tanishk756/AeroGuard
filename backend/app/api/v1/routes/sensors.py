"""Minimal F2 sensor registry endpoints."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies import require_permission
from app.models.sensor import Sensor
from app.models.user import User
from app.schemas.sensor import SensorResponse

router = APIRouter()


@router.get("/sensors", response_model=list[SensorResponse])
def list_sensors(db: Session = Depends(get_db), _: User = Depends(require_permission("sensors.read"))):
    return db.scalars(select(Sensor).order_by(Sensor.name, Sensor.id)).all()


@router.get("/sensors/{sensor_id}", response_model=SensorResponse)
def get_sensor(sensor_id: str, db: Session = Depends(get_db), _: User = Depends(require_permission("sensors.read"))):
    sensor = db.get(Sensor, sensor_id)
    if sensor is None:
        raise HTTPException(status_code=404, detail="Sensor not found")
    return sensor