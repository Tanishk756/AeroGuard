"""Incident analytics service implementing read-only SQL aggregations and metrics computation."""

from datetime import UTC, datetime, timedelta
import math
import statistics
from typing import Any

from sqlalchemy import case, func, select
from sqlalchemy.orm import Session

from app.models.incident import Incident, IncidentSeverity, IncidentStatus
from app.models.incident_event import DefensiveActionCategory, IncidentEvent, IncidentEventType
from app.schemas.incidents import (
    IncidentAnalyticsResponse,
    IncidentCorrelationMetrics,
    IncidentLifecycleTimingMetrics,
    IncidentProceduralActionMetrics,
    IncidentSeverityDistributionItem,
    IncidentStatusDistributionItem,
    IncidentSummaryMetrics,
    IncidentTimeSeriesBucket,
    IncidentWorkflowEventMetrics,
)


def _calc_percentiles(values: list[float]) -> tuple[float | None, float | None]:
    """Return (median, p95) in seconds rounded to 2 decimal places using standard math."""
    if not values:
        return None, None
    sorted_vals = sorted(values)
    med = float(statistics.median(sorted_vals))

    # Calculate 95th percentile using linear interpolation
    n = len(sorted_vals)
    if n == 1:
        p95 = sorted_vals[0]
    else:
        k = (n - 1) * 0.95
        f = math.floor(k)
        c = math.ceil(k)
        if f == c:
            p95 = sorted_vals[int(k)]
        else:
            p95 = sorted_vals[f] * (c - k) + sorted_vals[c] * (k - f)

    return round(med, 2), round(float(p95), 2)


def _format_bucket_date(dt: datetime, bucket_size: str) -> str:
    """Format datetime into a deterministic bucket string."""
    if bucket_size == "hour":
        return dt.strftime("%Y-%m-%d %H:00:00")
    elif bucket_size == "week":
        # Year + Week number (e.g. 2026-W34)
        return dt.strftime("%Y-W%U")
    else:
        # Default: day
        return dt.strftime("%Y-%m-%d")


class IncidentAnalyticsService:
    """Read-only operational analytics service over authoritative incident timeline data."""

    def __init__(self, db: Session):
        self.db = db

    def get_analytics(
        self,
        start_time: datetime | None = None,
        end_time: datetime | None = None,
        severity: IncidentSeverity | None = None,
        status: IncidentStatus | None = None,
        assigned_to: str | None = None,
        primary_track_id: str | None = None,
        primary_group_id: str | None = None,
        bucket_size: str = "day",
    ) -> IncidentAnalyticsResponse:
        """Compute deterministic descriptive analytics over matching incidents.

        Guarantees:
        - Read-only execution (zero database mutations).
        - SQL database aggregation for high-performance scale.
        - Strict non-kinetic, historical workflow scope.
        """
        # 1. Parameter Validation & Bounding
        if start_time is not None and end_time is not None:
            if start_time > end_time:
                raise ValueError("start_time must not be after end_time")
            if (end_time - start_time).days > 365:
                raise ValueError("Analytics window exceeds maximum allowed 365 days")

        if bucket_size not in ("hour", "day", "week"):
            bucket_size = "day"

        # 2. Build Base Incident Filters
        filters = []
        if start_time is not None:
            filters.append(Incident.created_at >= start_time)
        if end_time is not None:
            filters.append(Incident.created_at <= end_time)
        if severity is not None:
            filters.append(Incident.severity == severity)
        if status is not None:
            filters.append(Incident.status == status)
        if assigned_to is not None:
            filters.append(Incident.assigned_to == assigned_to)
        if primary_track_id is not None:
            filters.append(Incident.primary_track_id == primary_track_id)
        if primary_group_id is not None:
            filters.append(Incident.primary_group_id == primary_group_id)

        # 3. High-Performance SQL Aggregations (Summary & Distributions)
        summary_stmt = select(
            func.count(Incident.id).label("total"),
            func.sum(
                case(
                    (
                        Incident.status.in_(
                            [
                                IncidentStatus.NEW,
                                IncidentStatus.ACKNOWLEDGED,
                                IncidentStatus.TRIAGED,
                                IncidentStatus.ESCALATED,
                            ]
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("active"),
            func.sum(case((Incident.acknowledged_at.is_not(None), 1), else_=0)).label("acknowledged"),
            func.sum(
                case(
                    (
                        Incident.assigned_to.is_not(None) | Incident.assigned_at.is_not(None),
                        1,
                    ),
                    else_=0,
                )
            ).label("assigned"),
            func.sum(
                case(
                    (
                        Incident.status.in_(
                            [
                                IncidentStatus.TRIAGED,
                                IncidentStatus.ESCALATED,
                                IncidentStatus.RESOLVED,
                                IncidentStatus.CLOSED,
                            ]
                        ),
                        1,
                    ),
                    else_=0,
                )
            ).label("triaged"),
            func.sum(case((Incident.status == IncidentStatus.ESCALATED, 1), else_=0)).label("escalated"),
            func.sum(
                case(
                    (
                        (Incident.status.in_([IncidentStatus.RESOLVED, IncidentStatus.CLOSED]))
                        | (Incident.resolved_at.is_not(None)),
                        1,
                    ),
                    else_=0,
                )
            ).label("resolved"),
            func.sum(case((Incident.status == IncidentStatus.CLOSED, 1), else_=0)).label("closed"),
            # Severity counts
            func.sum(case((Incident.severity == IncidentSeverity.CRITICAL, 1), else_=0)).label("crit_cnt"),
            func.sum(case((Incident.severity == IncidentSeverity.HIGH, 1), else_=0)).label("high_cnt"),
            func.sum(case((Incident.severity == IncidentSeverity.MEDIUM, 1), else_=0)).label("med_cnt"),
            func.sum(case((Incident.severity == IncidentSeverity.LOW, 1), else_=0)).label("low_cnt"),
            # Status counts
            func.sum(case((Incident.status == IncidentStatus.NEW, 1), else_=0)).label("stat_new"),
            func.sum(case((Incident.status == IncidentStatus.ACKNOWLEDGED, 1), else_=0)).label("stat_ack"),
            func.sum(case((Incident.status == IncidentStatus.TRIAGED, 1), else_=0)).label("stat_triage"),
            func.sum(case((Incident.status == IncidentStatus.ESCALATED, 1), else_=0)).label("stat_esc"),
            func.sum(case((Incident.status == IncidentStatus.RESOLVED, 1), else_=0)).label("stat_res"),
            func.sum(case((Incident.status == IncidentStatus.CLOSED, 1), else_=0)).label("stat_cls"),
            # Correlation counts
            func.sum(case((Incident.primary_track_id.is_not(None), 1), else_=0)).label("with_track"),
            func.sum(case((Incident.primary_group_id.is_not(None), 1), else_=0)).label("with_group"),
            func.sum(
                case(
                    (
                        Incident.primary_track_id.is_(None) & Incident.primary_group_id.is_(None),
                        1,
                    ),
                    else_=0,
                )
            ).label("uncorrelated"),
        )
        if filters:
            summary_stmt = summary_stmt.where(*filters)

        row = self.db.execute(summary_stmt).one()

        total = row.total or 0
        active_cnt = row.active or 0
        ack_cnt = row.acknowledged or 0
        assign_cnt = row.assigned or 0
        triage_cnt = row.triaged or 0
        esc_cnt = row.escalated or 0
        res_cnt = row.resolved or 0
        cls_cnt = row.closed or 0

        crit_cnt = row.crit_cnt or 0
        high_cnt = row.high_cnt or 0
        med_cnt = row.med_cnt or 0
        low_cnt = row.low_cnt or 0

        stat_new = row.stat_new or 0
        stat_ack = row.stat_ack or 0
        stat_triage = row.stat_triage or 0
        stat_esc = row.stat_esc or 0
        stat_res = row.stat_res or 0
        stat_cls = row.stat_cls or 0

        with_track = row.with_track or 0
        with_group = row.with_group or 0
        uncorrelated = row.uncorrelated or 0

        summary_metrics = IncidentSummaryMetrics(
            total_incidents=total,
            active_incidents=active_cnt,
            acknowledged_incidents=ack_cnt,
            assigned_incidents=assign_cnt,
            triaged_incidents=triage_cnt,
            escalated_incidents=esc_cnt,
            resolved_incidents=res_cnt,
            closed_incidents=cls_cnt,
            critical_count=crit_cnt,
            high_count=high_cnt,
            medium_count=med_cnt,
            low_count=low_cnt,
        )

        # 4. Severity Distribution Percentages
        denom = float(total) if total > 0 else 1.0
        severity_dist: dict[IncidentSeverity, IncidentSeverityDistributionItem] = {
            IncidentSeverity.LOW: IncidentSeverityDistributionItem(
                count=low_cnt, percentage=round((low_cnt / denom) * 100, 2) if total > 0 else 0.0
            ),
            IncidentSeverity.MEDIUM: IncidentSeverityDistributionItem(
                count=med_cnt, percentage=round((med_cnt / denom) * 100, 2) if total > 0 else 0.0
            ),
            IncidentSeverity.HIGH: IncidentSeverityDistributionItem(
                count=high_cnt, percentage=round((high_cnt / denom) * 100, 2) if total > 0 else 0.0
            ),
            IncidentSeverity.CRITICAL: IncidentSeverityDistributionItem(
                count=crit_cnt, percentage=round((crit_cnt / denom) * 100, 2) if total > 0 else 0.0
            ),
        }

        # 5. Status Distribution Percentages
        status_dist: dict[IncidentStatus, IncidentStatusDistributionItem] = {
            IncidentStatus.NEW: IncidentStatusDistributionItem(
                count=stat_new, percentage=round((stat_new / denom) * 100, 2) if total > 0 else 0.0
            ),
            IncidentStatus.ACKNOWLEDGED: IncidentStatusDistributionItem(
                count=stat_ack, percentage=round((stat_ack / denom) * 100, 2) if total > 0 else 0.0
            ),
            IncidentStatus.TRIAGED: IncidentStatusDistributionItem(
                count=stat_triage, percentage=round((stat_triage / denom) * 100, 2) if total > 0 else 0.0
            ),
            IncidentStatus.ESCALATED: IncidentStatusDistributionItem(
                count=stat_esc, percentage=round((stat_esc / denom) * 100, 2) if total > 0 else 0.0
            ),
            IncidentStatus.RESOLVED: IncidentStatusDistributionItem(
                count=stat_res, percentage=round((stat_res / denom) * 100, 2) if total > 0 else 0.0
            ),
            IncidentStatus.CLOSED: IncidentStatusDistributionItem(
                count=stat_cls, percentage=round((stat_cls / denom) * 100, 2) if total > 0 else 0.0
            ),
        }

        # 6. Lifecycle Timing Calculations (Sample-extracted numpy math)
        ts_stmt = select(
            Incident.created_at,
            Incident.acknowledged_at,
            Incident.assigned_at,
            Incident.resolved_at,
            Incident.closed_at,
            Incident.status,
        )
        if filters:
            ts_stmt = ts_stmt.where(*filters)

        ts_rows = self.db.execute(ts_stmt).all()

        ack_deltas: list[float] = []
        assign_deltas: list[float] = []
        resolve_deltas: list[float] = []
        close_deltas: list[float] = []
        duration_deltas: list[float] = []

        now_utc = datetime.now(UTC).replace(tzinfo=None)

        for created_at, ack_at, assign_at, res_at, cls_at, inc_status in ts_rows:
            if ack_at and ack_at >= created_at:
                ack_deltas.append((ack_at - created_at).total_seconds())

            if assign_at and assign_at >= created_at:
                assign_deltas.append((assign_at - created_at).total_seconds())

            if res_at and res_at >= created_at:
                resolve_deltas.append((res_at - created_at).total_seconds())

            if cls_at and cls_at >= created_at:
                close_deltas.append((cls_at - created_at).total_seconds())

            # Lifetime / duration calculation
            end_t = cls_at or res_at
            if end_t and end_t >= created_at:
                duration_deltas.append((end_t - created_at).total_seconds())
            elif inc_status not in (IncidentStatus.RESOLVED, IncidentStatus.CLOSED):
                duration_deltas.append(max(0.0, (now_utc - created_at).total_seconds()))

        med_ack, p95_ack = _calc_percentiles(ack_deltas)
        med_assign, p95_assign = _calc_percentiles(assign_deltas)
        med_res, p95_res = _calc_percentiles(resolve_deltas)
        med_cls, p95_cls = _calc_percentiles(close_deltas)
        med_dur, p95_dur = _calc_percentiles(duration_deltas)

        timing_metrics = IncidentLifecycleTimingMetrics(
            median_acknowledgement_seconds=med_ack,
            p95_acknowledgement_seconds=p95_ack,
            median_assignment_seconds=med_assign,
            p95_assignment_seconds=p95_assign,
            median_resolution_seconds=med_res,
            p95_resolution_seconds=p95_res,
            median_closure_seconds=med_cls,
            p95_closure_seconds=p95_cls,
            median_duration_seconds=med_dur,
            p95_duration_seconds=p95_dur,
            sample_counts={
                "acknowledgement": len(ack_deltas),
                "assignment": len(assign_deltas),
                "resolution": len(resolve_deltas),
                "closure": len(close_deltas),
                "duration": len(duration_deltas),
            },
        )

        # 7. Time-Series Chronological Trend Bucketing
        inc_rows_stmt = select(
            Incident.created_at, Incident.resolved_at, Incident.closed_at, Incident.status
        )
        if filters:
            inc_rows_stmt = inc_rows_stmt.where(*filters)
        inc_rows_stmt = inc_rows_stmt.order_by(Incident.created_at.asc())

        inc_records = self.db.execute(inc_rows_stmt).all()

        bucket_map: dict[str, dict[str, int]] = {}

        for c_at, r_at, cl_at, st in inc_records:
            b_key = _format_bucket_date(c_at, bucket_size)
            if b_key not in bucket_map:
                bucket_map[b_key] = {"created": 0, "resolved": 0, "closed": 0, "escalated": 0}
            bucket_map[b_key]["created"] += 1
            if st == IncidentStatus.ESCALATED:
                bucket_map[b_key]["escalated"] += 1

            if r_at:
                rb_key = _format_bucket_date(r_at, bucket_size)
                if rb_key not in bucket_map:
                    bucket_map[rb_key] = {"created": 0, "resolved": 0, "closed": 0, "escalated": 0}
                bucket_map[rb_key]["resolved"] += 1

            if cl_at:
                cb_key = _format_bucket_date(cl_at, bucket_size)
                if cb_key not in bucket_map:
                    bucket_map[cb_key] = {"created": 0, "resolved": 0, "closed": 0, "escalated": 0}
                bucket_map[cb_key]["closed"] += 1

        time_series_buckets = [
            IncidentTimeSeriesBucket(
                bucket_start=key,
                created_count=val["created"],
                resolved_count=val["resolved"],
                closed_count=val["closed"],
                escalated_count=val["escalated"],
            )
            for key, val in sorted(bucket_map.items())
        ]

        # 8. Procedural Action Category Analytics
        action_stmt = (
            select(IncidentEvent.category, func.count(IncidentEvent.id))
            .join(Incident, IncidentEvent.incident_id == Incident.id)
            .where(IncidentEvent.category.is_not(None))
        )
        if filters:
            action_stmt = action_stmt.where(*filters)
        action_stmt = action_stmt.group_by(IncidentEvent.category)

        action_rows = self.db.execute(action_stmt).all()
        by_cat: dict[str, int] = {cat.value: 0 for cat in DefensiveActionCategory}
        total_actions = 0

        for cat_val, count in action_rows:
            key_str = cat_val.value if isinstance(cat_val, DefensiveActionCategory) else str(cat_val)
            by_cat[key_str] = count
            total_actions += count

        procedural_metrics = IncidentProceduralActionMetrics(
            by_category=by_cat,
            total_actions=total_actions,
        )

        # 9. Correlation Analytics & Top Entities
        top_tracks_stmt = (
            select(Incident.primary_track_id, func.count(Incident.id).label("cnt"))
            .where(Incident.primary_track_id.is_not(None))
        )
        if filters:
            top_tracks_stmt = top_tracks_stmt.where(*filters)
        top_tracks_stmt = (
            top_tracks_stmt.group_by(Incident.primary_track_id)
            .order_by(func.count(Incident.id).desc())
            .limit(5)
        )
        top_tracks = [
            {"track_id": trk_id, "incident_count": cnt}
            for trk_id, cnt in self.db.execute(top_tracks_stmt).all()
        ]

        top_groups_stmt = (
            select(Incident.primary_group_id, func.count(Incident.id).label("cnt"))
            .where(Incident.primary_group_id.is_not(None))
        )
        if filters:
            top_groups_stmt = top_groups_stmt.where(*filters)
        top_groups_stmt = (
            top_groups_stmt.group_by(Incident.primary_group_id)
            .order_by(func.count(Incident.id).desc())
            .limit(5)
        )
        top_groups = [
            {"group_id": grp_id, "incident_count": cnt}
            for grp_id, cnt in self.db.execute(top_groups_stmt).all()
        ]

        correlation_metrics = IncidentCorrelationMetrics(
            with_primary_track=with_track,
            with_primary_group=with_group,
            uncorrelated=uncorrelated,
            top_tracks=top_tracks,
            top_groups=top_groups,
        )

        # 10. Workflow Event Activity Analytics
        evt_stmt = (
            select(IncidentEvent.event_type, func.count(IncidentEvent.id))
            .join(Incident, IncidentEvent.incident_id == Incident.id)
        )
        if filters:
            evt_stmt = evt_stmt.where(*filters)
        evt_stmt = evt_stmt.group_by(IncidentEvent.event_type)

        evt_rows = self.db.execute(evt_stmt).all()
        by_evt_type: dict[str, int] = {et.value: 0 for et in IncidentEventType}
        tot_events = 0

        for et_val, count in evt_rows:
            key_str = et_val.value if isinstance(et_val, IncidentEventType) else str(et_val)
            by_evt_type[key_str] = count
            tot_events += count

        tot_notes = by_evt_type.get(IncidentEventType.NOTE_ADDED.value, 0)
        tot_act_logs = by_evt_type.get(IncidentEventType.ACTION_LOGGED.value, 0)

        workflow_metrics = IncidentWorkflowEventMetrics(
            by_event_type=by_evt_type,
            total_events=tot_events,
            total_notes=tot_notes,
            total_actions=tot_act_logs,
        )

        return IncidentAnalyticsResponse(
            window_start=start_time,
            window_end=end_time,
            bucket_size=bucket_size,
            summary=summary_metrics,
            timing=timing_metrics,
            severity_distribution=severity_dist,
            status_distribution=status_dist,
            time_series=time_series_buckets,
            procedural_actions=procedural_metrics,
            correlations=correlation_metrics,
            workflow=workflow_metrics,
        )
