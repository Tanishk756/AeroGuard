"""Single-detection ingestion endpoint."""

from datetime import UTC

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.database.session import get_db
from app.dependencies import require_permission
from app.ingestion.service import DetectionIngestionService
from app.models.user import User
from app.schemas.ingestion import DetectionIngestionRequest, DetectionIngestionResponse, RawDetection

router = APIRouter()


@router.post("/sensors/{sensor_id}/detections", response_model=DetectionIngestionResponse, status_code=status.HTTP_201_CREATED)
def ingest_detection(sensor_id: str, payload: DetectionIngestionRequest, response: Response, db: Session = Depends(get_db), _: User = Depends(require_permission("sensors.configure"))):
    raw = RawDetection(sensor_id=sensor_id, **payload.model_dump())
    try:
        result = DetectionIngestionService(db).ingest(raw)
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    except ValueError as exc:
        db.rollback()
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if not result.created:
        response.status_code = status.HTTP_200_OK
    return DetectionIngestionResponse(
        detection_id=result.detection.id,
        created=result.created,
        sensor_id=result.detection.sensor_id,
        source_detection_id=result.detection.source_detection_id,
        timestamp=result.detection.timestamp.replace(tzinfo=UTC),
    )