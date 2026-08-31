# Stage PR4 Implementation & Engineering Plan
## Asynchronous Task Processing, OpenTelemetry Tracing, Desktop Auto-Updater & Operator UX Refinement

## 1. Goal & Context
Stage PR4 bridges the remaining software capabilities gap between core production hardening (PR1–PR3) and full operational field deployment maturity. It addresses heavy synchronous task blocking, distributed tracing context propagation, secure native desktop software updates, and disconnected operator UI resilience without introducing unnecessary external dependencies.

---

## 2. Component Scope & Proposed Changes

### Phase 1: Asynchronous Task Queue & Worker Engine (P0)
- **Files Affected**:
  - `backend/app/core/tasks.py` [NEW]
  - `backend/app/api/v1/routes/incidents.py` [MODIFY]
  - `backend/requirements.txt` [MODIFY]
- **Implementation**:
  - Integrate an asynchronous worker task queue (`ARQ` backed by Redis) for offloading PDF generation and ZIP serialization.
  - Return HTTP 202 Accepted with task status tracking endpoint (`/api/v1/incidents/exports/tasks/{task_id}`).

### Phase 2: Desktop Signed Auto-Updater Plugin (P0)
- **Files Affected**:
  - `src-tauri/tauri.conf.json` [MODIFY]
  - `src-tauri/Cargo.toml` [MODIFY]
  - `src-tauri/src/lib.rs` [MODIFY]
- **Implementation**:
  - Integrate `tauri-plugin-updater` with Ed25519 public key verification.
  - Configure update manifest endpoint (`https://releases.aeroguard.internal/update.json`).

### Phase 3: OpenTelemetry Distributed Tracing & OTLP Exporter (P1)
- **Files Affected**:
  - `backend/app/core/telemetry.py` [NEW]
  - `backend/app/main.py` [MODIFY]
- **Implementation**:
  - Integrate OpenTelemetry FastAPI middleware to trace HTTP requests, database transactions, and background scheduler jobs.
  - Export standard OTLP trace spans when `AEROGUARD_OTEL_EXPORTER_OTLP_ENDPOINT` is configured.

### Phase 4: Tactical Acoustic Alert Synthesizer & Offline Map Storage (P1)
- **Files Affected**:
  - `apps/operator/src/services/audioAlerts.ts` [NEW]
  - `apps/operator/src/services/offlineTileCache.ts` [NEW]
  - `apps/operator/src/components/TacticalMap.tsx` [MODIFY]
- **Implementation**:
  - Synthesize Web Audio API acoustic alarm tones for `CRITICAL` threat escalation alerts (configurable mute/volume).
  - Cache map tiles in IndexedDB to allow tactical map rendering during disconnected / offline operations.

---

## 3. Verification Plan

### Automated Tests
- `pytest backend/tests/test_pr4_async_tasks.py` (Verify task queue submission & result retrieval)
- `pytest backend/tests/test_pr4_telemetry.py` (Verify OpenTelemetry span creation and correlation ID propagation)
- `npm --prefix apps/operator test` (Verify Web Audio synthesizer & IndexedDB tile cache unit tests)
- `cargo check --manifest-path src-tauri/Cargo.toml` (Verify Tauri updater compilation)

### Manual Verification
- Execute incident PDF export and observe immediate HTTP 202 response with background task execution.
- Simulate disconnected network in operator console and verify cached map tile rendering.
