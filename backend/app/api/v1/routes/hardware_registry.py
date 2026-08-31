"""Stage S4 Hardware Registry REST API Routes.

Provides CRUD management and category filtering for hardware components.
"""

import uuid
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.hardware_registry import PersistentHardwareComponent
from app.schemas.hardware_registry import (
    HardwareCategory,
    HardwareComponentCreate,
    HardwareComponentResponse,
)

router = APIRouter(prefix="/hardware", tags=["hardware_registry"])


@router.get("/categories", response_model=List[str])
def list_hardware_categories():
    """GET /api/v1/hardware/categories - List available hardware component categories."""
    return [c.value for c in HardwareCategory]


@router.get("", response_model=List[HardwareComponentResponse])
def list_hardware_components(
    category: Optional[str] = Query(None, description="Filter by hardware category"),
    manufacturer: Optional[str] = Query(None, description="Filter by manufacturer name"),
    search: Optional[str] = Query(None, description="Free text search query"),
    db: Session = Depends(get_db),
):
    """GET /api/v1/hardware - Query hardware components catalog."""
    query = select(PersistentHardwareComponent)

    if category:
        query = query.where(PersistentHardwareComponent.category == category.lower())
    if manufacturer:
        query = query.where(PersistentHardwareComponent.manufacturer.ilike(f"%{manufacturer}%"))
    if search:
        query = query.where(
            (PersistentHardwareComponent.model.ilike(f"%{search}%"))
            | (PersistentHardwareComponent.manufacturer.ilike(f"%{search}%"))
        )

    return db.scalars(query.order_by(PersistentHardwareComponent.created_at.desc())).all()


@router.get("/{hardware_id}", response_model=HardwareComponentResponse)
def get_hardware_component(hardware_id: str, db: Session = Depends(get_db)):
    """GET /api/v1/hardware/{id} - Get hardware component by ID."""
    comp = db.get(PersistentHardwareComponent, hardware_id)
    if not comp:
        raise HTTPException(status_code=404, detail=f"Hardware component '{hardware_id}' not found")
    return comp


@router.post("", response_model=HardwareComponentResponse, status_code=status.HTTP_201_CREATED)
def create_hardware_component(payload: HardwareComponentCreate, db: Session = Depends(get_db)):
    """POST /api/v1/hardware - Add new component to hardware registry catalog."""
    comp = PersistentHardwareComponent(
        id=str(uuid.uuid4()),
        manufacturer=payload.manufacturer,
        model=payload.model,
        category=payload.category.value,
        part_number=payload.part_number,
        datasheet_url=payload.datasheet_url,
        mass_g=payload.mass_g,
        dimensions_mm=payload.dimensions_mm,
        electrical_specs=payload.electrical_specs,
        interfaces=payload.interfaces,
        supported_simulation_models=payload.supported_simulation_models,
        metadata_json=payload.metadata_json,
    )
    db.add(comp)
    db.commit()
    db.refresh(comp)
    return comp


@router.put("/{hardware_id}", response_model=HardwareComponentResponse)
def update_hardware_component(hardware_id: str, payload: HardwareComponentCreate, db: Session = Depends(get_db)):
    """PUT /api/v1/hardware/{id} - Update existing hardware component specifications."""
    comp = db.get(PersistentHardwareComponent, hardware_id)
    if not comp:
        raise HTTPException(status_code=404, detail=f"Hardware component '{hardware_id}' not found")

    comp.manufacturer = payload.manufacturer
    comp.model = payload.model
    comp.category = payload.category.value
    comp.part_number = payload.part_number
    comp.datasheet_url = payload.datasheet_url
    comp.mass_g = payload.mass_g
    comp.dimensions_mm = payload.dimensions_mm
    comp.electrical_specs = payload.electrical_specs
    comp.interfaces = payload.interfaces
    comp.supported_simulation_models = payload.supported_simulation_models
    comp.metadata_json = payload.metadata_json

    db.commit()
    db.refresh(comp)
    return comp


@router.delete("/{hardware_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_hardware_component(hardware_id: str, db: Session = Depends(get_db)):
    """DELETE /api/v1/hardware/{id} - Delete component from hardware registry catalog."""
    comp = db.get(PersistentHardwareComponent, hardware_id)
    if not comp:
        raise HTTPException(status_code=404, detail=f"Hardware component '{hardware_id}' not found")
    db.delete(comp)
    db.commit()
    return None
