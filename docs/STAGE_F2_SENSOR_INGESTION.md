# Stage F2 Sensor Abstraction and Detection Ingestion

Stage F2 adds the first operational data pipeline:

```text
SensorAdapter -> RawDetection -> validation -> normalization -> F1 Detection -> SQLite
```

F2 owns adapter contracts, raw detection validation, canonical normalization,
sensor lookup, idempotent persistence, offline simulation/replay adapters, and
minimal sensor/detection APIs. F3 owns association and tracks. F4 owns alerts
and threat prioritization. Tracking, fusion, alerting, threat assessment,
scenario execution, realtime delivery, AI/ML, and hardware DSP are not part of
F2.

## Adapter boundary

`SensorAdapter` is a synchronous Python protocol exposing `sensor_id`,
`source_type`, `source_class`, and `read()`. Adapters return typed
`RawDetection` values and never mutate persistent sensor state. F2 includes a
fixed-seed simulation adapter and a local JSONL replay adapter. Both are
offline and deterministic; no physics, network, or hardware SDK is involved.

## Validation and normalization

Raw values use WGS84-compatible degrees, meters, meters/second, degrees for
heading, meters for uncertainty, and timezone-aware UTC timestamps. The
normalizer converts timestamps to F1's naive-UTC database representation,
normalizes exactly 360 degrees to 0, preserves provenance, and rejects invalid
coordinates, non-finite values, negative values, invalid confidence, malformed
metadata, source mismatches, and future real/simulation timestamps beyond five
minutes. Historical and replay timestamps are preserved and are not reordered.
No bad value is silently clamped.

Metadata is bounded using the existing operational contract limits: six levels,
100 collection items, 512-character strings/keys, and 16 KiB serialized JSON.

## Ingestion and duplicates

`DetectionIngestionService` resolves the sensor server-side, rejects unknown
or disabled sensors, validates and normalizes before writing, and owns one
transaction per detection. It uses the F1 `(sensor_id, source_detection_id)`
uniqueness boundary. A first submission returns `created=true`; a retry returns
the existing immutable detection with `created=false`. Concurrent uniqueness
races use a nested savepoint and never overwrite the original payload.

The service returns a frozen `DetectionIngested` operational result. This is
separate from Stage E `AuditEvent`: detection telemetry is not audited per
record. Future administrative sensor changes may use Stage E audit events.

## API and security

F2 exposes only:

- `GET /api/v1/sensors` with `sensors.read`
- `GET /api/v1/sensors/{sensor_id}` with `sensors.read`
- `POST /api/v1/sensors/{sensor_id}/detections` with `sensors.configure`

The route sensor ID is authoritative and is injected into the raw contract;
clients cannot select another sensor through the body. New detections return
201 and duplicates return 200. Unknown sensors return 404, disabled sensors
return 403, and request validation returns the existing structured 422 format.
No actor, role, permission, track, threat, or ownership data is accepted from
clients. Request-size/rate limiting and batch ingestion remain deferred.

Administrative sensor state remains separate from adapter runtime health. An
adapter failure never changes persistent sensor status automatically.

## Persistence and limitations

F2 uses the existing F1 SQLite schema and adds no migration or dependency.
Transactions are intentionally short and adapter I/O occurs outside database
transactions. SQLite is appropriate for the initial local-first workload;
writer contention and throughput must be measured before considering batching,
a queue, or another database. No tracking, alert, threat, scenario,
WebSocket, broker, cloud service, or frontend functionality is included.
