# AeroGuard Stage PR4 Operations & Deployment Runbook

## 1. Overview
This runbook describes operational procedures for managing asynchronous task processing, OpenTelemetry tracing configuration, Tauri desktop signed auto-updater releases, and operator offline map caching.

---

## 2. Environment Variables

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `AEROGUARD_TASKS_ENABLED` | `true` | Enables background task worker execution |
| `AEROGUARD_TASK_MAX_RETRIES` | `3` | Maximum retry attempts for failed background tasks |
| `AEROGUARD_OTEL_ENABLED` | `true` | Enables OpenTelemetry distributed tracing middleware |
| `AEROGUARD_OTEL_ENDPOINT` | `http://localhost:4317` | OTLP gRPC/HTTP collector endpoint |

---

## 3. Asynchronous Export Task Operations

### Submit Asynchronous Incident Export
```bash
curl -X POST "http://localhost:8000/api/v1/incidents/export/async" \
     -H "Content-Type: application/json" \
     -H "Authorization: Bearer <TOKEN>" \
     -d '{"format": "JSON", "limit": 50}'
```
Response (`HTTP 202 Accepted`):
```json
{
  "task_id": "a1b2c3d4-5678-90ab-cdef-1234567890ab",
  "status": "QUEUED",
  "message": "Export task queued for background execution"
}
```

### Poll Task Status & Metadata
```bash
curl -X GET "http://localhost:8000/api/v1/incidents/export/tasks/a1b2c3d4-5678-90ab-cdef-1234567890ab" \
     -H "Authorization: Bearer <TOKEN>"
```

---

## 4. Tauri Desktop Signed Auto-Updater Release Procedure

### Generating Ed25519 Signing Keys
```bash
npx tauri signer generate -w ~/.tauri/aeroguard.key
```

### Configuring GitHub Secrets for Release CI
Set the following secrets in repository settings:
- `TAURI_SIGNING_PRIVATE_KEY`: Content of private key `aeroguard.key`
- `TAURI_SIGNING_PRIVATE_KEY_PASSWORD`: Key passphrase (if set)

### Updating Release Manifest (`update.json`)
Upload manifest to update endpoint (`https://releases.aeroguard.internal/update.json`):
```json
{
  "version": "0.2.0",
  "notes": "AeroGuard Stage PR4 Security & Performance Update",
  "pub_date": "2026-08-31T12:00:00Z",
  "platforms": {
    "windows-x86_64": {
      "signature": "dW50cnVzdGVkIGNvbW1lbnQ6IHNpZ25hdHVyZQ...",
      "url": "https://releases.aeroguard.internal/AeroGuard_0.2.0_x64-setup.nsis.zip"
    }
  }
}
```
