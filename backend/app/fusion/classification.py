"""Confidence-weighted multi-source classification reconciliation."""

from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.association import TrackAssociation
from app.models.detection import Detection
from app.models.track import Track


@dataclass(frozen=True)
class ClassificationReconciliation:
    reconciled_classification: str | None
    evidence_scores: dict[str, float]
    total_votes: int


def reconcile_classification(
    db: Session,
    track: Track,
    latest_detection: Detection | None = None,
    window_seconds: float = 60.0,
) -> ClassificationReconciliation:
    """Reconcile track classification using confidence-weighted evidence accumulation.

    Accumulates confidence points per observed classification label across the recent
    association window. The label with the highest accumulated evidence score wins.
    Ties are broken deterministically by lexical order.
    """
    scores: dict[str, float] = {}
    total_votes = 0

    eval_time = latest_detection.timestamp if latest_detection else track.last_seen_at
    window_start = eval_time - timedelta(seconds=window_seconds)

    # Query recent associated detections
    query = (
        select(Detection.classification, Detection.confidence)
        .join(TrackAssociation, TrackAssociation.detection_id == Detection.id)
        .where(
            TrackAssociation.track_id == track.id,
            TrackAssociation.timestamp >= window_start,
            Detection.classification.is_not(None),
        )
    )
    results = db.execute(query).all()

    for cls_name, conf in results:
        if cls_name:
            scores[cls_name] = round(scores.get(cls_name, 0.0) + float(conf), 4)
            total_votes += 1

    # Include latest detection if provided and not yet queried
    if latest_detection and latest_detection.classification:
        if total_votes == 0:
            scores[latest_detection.classification] = round(
                scores.get(latest_detection.classification, 0.0) + float(latest_detection.confidence), 4
            )
            total_votes += 1

    if not scores:
        return ClassificationReconciliation(
            reconciled_classification=track.classification,
            evidence_scores={},
            total_votes=0,
        )

    # Deterministic winner selection: highest score, tie-break by lexical classification name
    winner = sorted(scores.keys(), key=lambda k: (-scores[k], k))[0]

    return ClassificationReconciliation(
        reconciled_classification=winner,
        evidence_scores=scores,
        total_votes=total_votes,
    )
