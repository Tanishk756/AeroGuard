"""Stage S6 World & World Object Management REST API Routes."""

import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.models.scenario_world import PersistentSimulationWorld, PersistentWorldObject
from app.schemas.scenario_world import SimulationWorldSpec, WorldObjectSpec

router = APIRouter(prefix="/worlds", tags=["Worlds"])


@router.post("", response_model=SimulationWorldSpec, status_code=status.HTTP_201_CREATED)
def create_world(payload: SimulationWorldSpec, db: Session = Depends(get_db)):
    """POST /api/v1/worlds - Create a new simulator-neutral world environment."""
    world_id = payload.id or f"world-{uuid.uuid4().hex[:8]}"
    world = PersistentSimulationWorld(
        id=world_id,
        project_id=payload.project_id,
        name=payload.name,
        world_type=payload.world_type,
        description=payload.description,
    )
    db.add(world)
    db.commit()

    for obj in payload.objects:
        obj_entity = PersistentWorldObject(
            id=f"wobj-{uuid.uuid4().hex[:8]}",
            world_id=world.id,
            object_type=obj.object_type,
            position_json=obj.position,
            orientation_json=obj.orientation,
            scale_json=obj.scale,
            collision_enabled=obj.collision_enabled,
            visual_enabled=obj.visual_enabled,
            metadata_json=obj.metadata,
        )
        db.add(obj_entity)

    db.commit()
    db.refresh(world)

    objects_resp = [
        WorldObjectSpec(
            id=o.id,
            object_type=o.object_type,
            position=o.position_json,
            orientation=o.orientation_json,
            scale=o.scale_json,
            collision_enabled=o.collision_enabled,
            visual_enabled=o.visual_enabled,
            metadata=o.metadata_json,
        )
        for o in world.objects
    ]

    return SimulationWorldSpec(
        id=world.id,
        project_id=world.project_id,
        name=world.name,
        world_type=world.world_type,
        description=world.description,
        objects=objects_resp,
    )


@router.get("", response_model=List[SimulationWorldSpec])
def list_worlds(db: Session = Depends(get_db)):
    """GET /api/v1/worlds - List all available simulation worlds."""
    worlds = db.scalars(select(PersistentSimulationWorld)).all()
    result = []
    for w in worlds:
        objs = [
            WorldObjectSpec(
                id=o.id,
                object_type=o.object_type,
                position=o.position_json,
                orientation=o.orientation_json,
                scale=o.scale_json,
                collision_enabled=o.collision_enabled,
                visual_enabled=o.visual_enabled,
            )
            for o in w.objects
        ]
        result.append(
            SimulationWorldSpec(
                id=w.id,
                project_id=w.project_id,
                name=w.name,
                world_type=w.world_type,
                description=w.description,
                objects=objs,
            )
        )
    return result


@router.post("/{world_id}/objects", response_model=WorldObjectSpec, status_code=status.HTTP_201_CREATED)
def add_world_object(world_id: str, obj: WorldObjectSpec, db: Session = Depends(get_db)):
    """POST /api/v1/worlds/{id}/objects - Add a static box, cylinder, or landing pad object to a world."""
    world = db.get(PersistentSimulationWorld, world_id)
    if not world:
        raise HTTPException(status_code=404, detail=f"World '{world_id}' not found")

    obj_id = f"wobj-{uuid.uuid4().hex[:8]}"
    obj_entity = PersistentWorldObject(
        id=obj_id,
        world_id=world_id,
        object_type=obj.object_type,
        position_json=obj.position,
        orientation_json=obj.orientation,
        scale_json=obj.scale,
        collision_enabled=obj.collision_enabled,
        visual_enabled=obj.visual_enabled,
        metadata_json=obj.metadata,
    )
    db.add(obj_entity)
    db.commit()

    return WorldObjectSpec(
        id=obj_id,
        object_type=obj.object_type,
        position=obj.position,
        orientation=obj.orientation,
        scale=obj.scale,
        collision_enabled=obj.collision_enabled,
        visual_enabled=obj.visual_enabled,
    )
