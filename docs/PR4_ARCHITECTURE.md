# AeroGuard Stage PR4 Architecture Specification
## Asynchronous Task Processing, OpenTelemetry Tracing, Desktop Auto-Updater & Operator UX Refinement

## 1. Overview
Stage PR4 extends the AeroGuard platform architecture across four primary dimensions:
1. **Asynchronous Background Task Queue & Worker Engine**: Offloading synchronous heavy PDF and ZIP exports to an asynchronous background worker.
2. **OpenTelemetry Distributed Tracing**: Injecting trace context headers (`traceparent`) and standard OTLP span attributes across FastAPI HTTP routes.
3. **Signed Tauri Desktop Auto-Updater**: Configuring Ed25519 signature verification and HTTPS update manifest endpoints in the desktop client.
4. **Operator UX & Offline Resilience**: Adding Web Audio API acoustic threat alert synthesis and IndexedDB offline map tile storage in the React operator console.

---

## 2. Topology & Data Flow

```
                     +-----------------------------------+
                     |      REACT OPERATOR UI / TAURI    |
                     |  (Web Audio Alerts, Tile Cache)   |
                     +-----------------+-----------------+
                                       |
                                       v HTTP / WSS
                     +-----------------+-----------------+
                     |       NGINX REVERSE PROXY         |
                     +-----------------+-----------------+
                                       |
                                       v HTTP 202 Accepted
                     +-----------------+-----------------+
                     |      AEROGUARD FASTAPI API        |
                     |  (OTel Tracing, Security, Auth)   |
                     +--------+----------------+---------+
                              |                |
             Task Dispatch    |                | Task Queue
                              v                v
                     +--------+-------+   +----+----+
                     | TASK MANAGER   |   | REDIS 7 |
                     | (Worker Thread)|   +---------+
                     +----------------+
```

---

## 3. Asynchronous Task Lifecycle State Machine

```
   +--------+      Dispatch      +---------+      Worker Success     +-----------+
   | QUEUED | -----------------> | RUNNING | ----------------------> | SUCCEEDED |
   +--------+                    +----+----+                         +-----------+
       ^                              |
       |       Retry (Attempt < Max)  | Worker Exception
       +------------------------------+
                                      |
                                      v Retry Exhausted
                                 +----+----+
                                 | FAILED  |
                                 +---------+
```

---

## 4. OpenTelemetry Attribute Redaction Policy
To prevent privacy or credential leaks in distributed traces, the following attributes are **strictly sanitized** to `[REDACTED]`:
- `password`, `token`, `access_token`, `jwt`, `secret`, `authorization`, `cookie`, `user_id`, `username`, `incident_id`, `track_id`, `session_id`.
