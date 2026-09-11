"""Stage S8 Sensor & Payload Digital Twin REST API Routes."""

import uuid
from typing import List, Optional, Dict, Any
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.hardware_registry import PersistentVehicle
from app.models.sensor_payload import PersistentSensorInstance, PersistentPayloadInstance
from app.schemas.sensor_payload import (
    SensorInstanceSpec,
    PayloadInstanceSpec,
    PowerBudgetBreakdown,
)
from app.simulation.core.failure_injection import SimulationFailureInjector
from app.simulation.core.battery_model import BatteryEnergyEngine
from app.simulation.core.vehicle_calculator import VehicleCalculator

router = APIRouter(tags=["sensors_payloads"])


@router.post("/vehicles/{vehicle_id}/sensors", response_model=SensorInstanceSpec, status_code=status.HTTP_201_CREATED)
def add_sensor_instance(
    vehicle_id: str,
    payload: SensorInstanceSpec,
    db: Session = Depends(get_db)
):
    """POST /api/v1/vehicles/{vehicle_id}/sensors - Add sensor instance to vehicle digital twin."""
    vehicle = db.get(PersistentVehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_id}' not found")

    sensor_id = payload.id or str(uuid.uuid4())
    sensor_entity = PersistentSensorInstance(
        id=sensor_id,
        vehicle_id=vehicle_id,
        sensor_type=payload.sensor_type,
        name=payload.name,
        mass_g=payload.mass_g,
        power_w=payload.power_w,
        position_json=payload.position,
        orientation_json=payload.orientation,
        update_rate_hz=payload.update_rate_hz,
        health_status=payload.health_status,
        config_json=payload.config,
    )

    db.add(sensor_entity)
    db.commit()
    db.refresh(sensor_entity)

    return SensorInstanceSpec(
        id=sensor_entity.id,
        vehicle_id=sensor_entity.vehicle_id,
        sensor_type=sensor_entity.sensor_type,
        name=sensor_entity.name,
        mass_g=sensor_entity.mass_g,
        power_w=sensor_entity.power_w,
        position=sensor_entity.position_json,
        orientation=sensor_entity.orientation_json,
        update_rate_hz=sensor_entity.update_rate_hz,
        health_status=sensor_entity.health_status,
        config=sensor_entity.config_json,
    )


@router.get("/vehicles/{vehicle_id}/sensors", response_model=List[SensorInstanceSpec])
def list_sensor_instances(vehicle_id: str, db: Session = Depends(get_db)):
    """GET /api/v1/vehicles/{vehicle_id}/sensors - List sensor instances attached to vehicle."""
    vehicle = db.get(PersistentVehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_id}' not found")

    sensors = db.scalars(
        select(PersistentSensorInstance).where(PersistentSensorInstance.vehicle_id == vehicle_id)
    ).all()

    return [
        SensorInstanceSpec(
            id=s.id,
            vehicle_id=s.vehicle_id,
            sensor_type=s.sensor_type,
            name=s.name,
            mass_g=s.mass_g,
            power_w=s.power_w,
            position=s.position_json,
            orientation=s.orientation_json,
            update_rate_hz=s.update_rate_hz,
            health_status=s.health_status,
            config=s.config_json,
        )
        for s in sensors
    ]


@router.delete("/vehicles/{vehicle_id}/sensors/{sensor_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_sensor_instance(vehicle_id: str, sensor_id: str, db: Session = Depends(get_db)):
    """DELETE /api/v1/vehicles/{vehicle_id}/sensors/{sensor_id} - Detach sensor instance."""
    sensor = db.get(PersistentSensorInstance, sensor_id)
    if not sensor or sensor.vehicle_id != vehicle_id:
        raise HTTPException(status_code=404, detail=f"Sensor '{sensor_id}' not found on vehicle '{vehicle_id}'")

    db.delete(sensor)
    db.commit()
    return None


@router.post("/vehicles/{vehicle_id}/payloads", response_model=PayloadInstanceSpec, status_code=status.HTTP_201_CREATED)
def add_payload_instance(
    vehicle_id: str,
    payload: PayloadInstanceSpec,
    db: Session = Depends(get_db)
):
    """POST /api/v1/vehicles/{vehicle_id}/payloads - Attach payload to vehicle digital twin."""
    vehicle = db.get(PersistentVehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_id}' not found")

    payload_id = payload.id or str(uuid.uuid4())
    payload_entity = PersistentPayloadInstance(
        id=payload_id,
        vehicle_id=vehicle_id,
        payload_type=payload.payload_type,
        name=payload.name,
        mass_g=payload.mass_g,
        power_w=payload.power_w,
        position_json=payload.position,
        orientation_json=payload.orientation,
        config_json=payload.config,
    )

    db.add(payload_entity)
    db.commit()
    db.refresh(payload_entity)

    return PayloadInstanceSpec(
        id=payload_entity.id,
        vehicle_id=payload_entity.vehicle_id,
        payload_type=payload_entity.payload_type,
        name=payload_entity.name,
        mass_g=payload_entity.mass_g,
        power_w=payload_entity.power_w,
        position=payload_entity.position_json,
        orientation=payload_entity.orientation_json,
        config=payload_entity.config_json,
    )


@router.get("/vehicles/{vehicle_id}/payloads", response_model=List[PayloadInstanceSpec])
def list_payload_instances(vehicle_id: str, db: Session = Depends(get_db)):
    """GET /api/v1/vehicles/{vehicle_id}/payloads - List payload instances attached to vehicle."""
    vehicle = db.get(PersistentVehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_id}' not found")

    payloads = db.scalars(
        select(PersistentPayloadInstance).where(PersistentPayloadInstance.vehicle_id == vehicle_id)
    ).all()

    return [
        PayloadInstanceSpec(
            id=p.id,
            vehicle_id=p.vehicle_id,
            payload_type=p.payload_type,
            name=p.name,
            mass_g=p.mass_g,
            power_w=p.power_w,
            position=p.position_json,
            orientation=p.orientation_json,
            config=p.config_json,
        )
        for p in payloads
    ]


@router.delete("/vehicles/{vehicle_id}/payloads/{payload_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_payload_instance(vehicle_id: str, payload_id: str, db: Session = Depends(get_db)):
    """DELETE /api/v1/vehicles/{vehicle_id}/payloads/{payload_id} - Detach payload instance."""
    payload_ent = db.get(PersistentPayloadInstance, payload_id)
    if not payload_ent or payload_ent.vehicle_id != vehicle_id:
        raise HTTPException(status_code=404, detail=f"Payload '{payload_id}' not found on vehicle '{vehicle_id}'")

    db.delete(payload_ent)
    db.commit()
    return None


@router.get("/vehicles/{vehicle_id}/power-budget", response_model=PowerBudgetBreakdown)
def get_vehicle_power_budget(vehicle_id: str, db: Session = Depends(get_db)):
    """GET /api/v1/vehicles/{vehicle_id}/power-budget - Calculate power budget breakdown."""
    vehicle = db.get(PersistentVehicle, vehicle_id)
    if not vehicle:
        raise HTTPException(status_code=404, detail=f"Vehicle '{vehicle_id}' not found")

    sensors = db.scalars(
        select(PersistentSensorInstance).where(PersistentSensorInstance.vehicle_id == vehicle_id)
    ).all()
    payloads = db.scalars(
        select(PersistentPayloadInstance).where(PersistentPayloadInstance.vehicle_id == vehicle_id)
    ).all()

    avionics_power_w = 5.0  # Base FC + Receiver power
    sensor_power_w = sum(s.power_w for s in sensors)
    payload_power_w = sum(p.power_w for p in payloads)
    non_propulsion_w = avionics_power_w + sensor_power_w + payload_power_w

    battery_dynamics = BatteryEnergyEngine.evaluate_battery(
        vehicle.battery, vehicle.total_mass_g / 1000.0, vehicle.estimated_hover_throttle, num_motors=4
    )
    estimated_hover_power_w = battery_dynamics.get("estimated_hover_power_w", 200.0) + non_propulsion_w

    return PowerBudgetBreakdown(
        avionics_power_w=avionics_power_w,
        sensor_power_w=sensor_power_w,
        payload_power_w=payload_power_w,
        total_non_propulsion_power_w=non_propulsion_w,
        estimated_hover_power_w=estimated_hover_power_w,
    )


@router.post("/simulation/fail-sensor")
def inject_sensor_failure_endpoint(payload: Dict[str, Any]):
    """POST /api/v1/simulation/fail-sensor - Inject sensor fault into simulation channel."""
    run_id = payload.get("run_id")
    sensor_type = payload.get("sensor_type")
    fault_type = payload.get("fault_type", "FAILED")

    if not run_id or not sensor_type:
        raise HTTPException(status_code=400, detail="run_id and sensor_type are required")

    return SimulationFailureInjector.inject_sensor_failure(run_id, sensor_type, fault_type)
