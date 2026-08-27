# UI8 — Desktop and Native Packaging (Tauri 2 Integration)

## 1. Executive Summary

Stage UI8 establishes the native Windows desktop distribution of the AeroGuard Operator Console using **Tauri 2.x**. It packages the existing production React frontend into a lightweight, secure Windows desktop application while maintaining complete, unimpaired operation in standard web browsers.

AeroGuard Desktop introduces:
- **Tauri 2 Foundation**: Minimal Rust desktop shell with strict capability gating (`core:default`, `notification:default`).
- **Desktop Environment Bridge**: Typed TypeScript API abstraction with graceful browser fallbacks (`apps/operator/src/api/desktop.ts`, `apps/operator/src/hooks/useDesktopEnvironment.ts`).
- **Tactical Window Titlebar**: Custom dark tactical window titlebar (`apps/operator/src/components/desktop/DesktopTitlebar.tsx`) with branding, live connectivity indicator, drag region, and window controls (minimize, maximize/restore, close).
- **Native OS Notifications**: Desktop notifications for `CRITICAL` and `HIGH` operational alerts using `@tauri-apps/plugin-notification`.
- **Bounded In-Memory Deduplication**: Prevents alert notification spam without persistent disk/storage caching.
- **System Tray Integration**: Native tray icon with tooltip, window toggle (show/unminimize/focus), and clean exit.
- **Dual Distributable Windows Packaging**: Generates both standalone `.exe` binaries, Windows Installer `.msi` packages (via WiX 3.14), and setup `.exe` installers (via NSIS 3.11).

---

## 2. Architecture & Dual-Mode Operation

AeroGuard maintains a single unified React codebase across Web and Desktop environments.

```
                  ┌──────────────────────────────────────────────────┐
                  │          AeroGuard Operator Console              │
                  │             (React 18 + Vite)                    │
                  └─────────────────────────┬────────────────────────┘
                                            │
                    ┌───────────────────────┴───────────────────────┐
                    ▼                                               ▼
         [ Web Browser Mode ]                            [ Tauri Desktop Mode ]
     isTauri() === false                             isTauri() === true
     • Standard Header Layout                        • Tactical Window Titlebar
     • Window Controls: No-Op                        • Window Controls: Native Win32
     • Notifications: Suppressed                     • Notifications: Windows Toast (WinRT)
     • No System Tray                                • System Tray: Enabled
     • Direct HTTP/Cookie Session                    • Direct HTTP/Cookie Session (Shared)
```

### 2.1 Environmental Gating
- **`isTauri()`**: Checks for `window.__TAURI_INTERNALS__` or `window.__TAURI__`.
- **Browser Fallback**: All desktop window and notification functions safely return defaults or no-op when executing in standard browsers, preventing crashes or runtime exceptions.
- **Authentication Continuity**: Both modes utilize the same HttpOnly cookie-based session architecture communicating with the FastAPI backend (`http://127.0.0.1:8000`). No token or credential persistence is introduced.

---

## 3. Desktop Subsystems

### 3.1 Desktop API Bridge & Hook
- **`apps/operator/src/api/desktop.ts`**: Provides strongly-typed helper methods:
  - `isTauri(): boolean`
  - `minimizeWindow(): Promise<void>`
  - `maximizeWindow(): Promise<void>`
  - `unmaximizeWindow(): Promise<void>`
  - `toggleMaximizeWindow(): Promise<boolean>`
  - `isWindowMaximized(): Promise<boolean>`
  - `closeWindow(): Promise<void>`
  - `toggleFullscreen(): Promise<boolean>`
  - `sendDesktopNotification(options): Promise<boolean>`
  - `dispatchAlertNotifications(alerts, isOnline): Promise<number>`
  - `isAlertSeverityEligible(alert): boolean`
  - `sanitizeNotificationBody(text): string`
  - `AlertNotificationDeduplicator`: In-memory bounded cache (max capacity: 100).
- **`apps/operator/src/hooks/useDesktopEnvironment.ts`**: React hook providing reactive window state (`isDesktop`, `isMaximized`, `isOnline`), backend health polling (`/health`), and dynamic resize event listeners with cleanup on unmount.

### 3.2 Custom Tactical Titlebar
- **`apps/operator/src/components/desktop/DesktopTitlebar.tsx`**:
  - Drag region enabled via `data-tauri-drag-region`.
  - Left branding: `🛡️ AEROGUARD | Operator Console` with live connectivity status pill (`● ONLINE` / `● OFFLINE`).
  - Right controls: Minimize (`🗕`), Maximize/Restore (`🗖` / `🗗`), and Close (`✕`).
  - Accessible button attributes (`aria-label`, `title`, keyboard focus states).

### 3.3 Native Notifications & In-Memory Deduplication
- **Severity Rules**:
  - `CRITICAL` (Status `OPEN`) → Emits native OS notification.
  - `HIGH` (Status `OPEN`) → Emits native OS notification.
  - `MEDIUM` / `LOW` / `INFO` → Suppressed (no native notification).
  - Non-`OPEN` alerts (`ACKNOWLEDGED`, `RESOLVED`) → Suppressed.
- **Offline Suppression**: Notifications are suppressed if backend connectivity is offline.
- **Payload Sanitization**: Redacts sensitive terms (tokens, bearer headers, passwords) and caps text length to 200 characters for clean OS toast rendering.
- **Deduplication Key**: `${alert.id}:${alert.status}:${alert.severity}` stored in-memory. Bounded to 100 entries with automatic oldest-30 eviction.

### 3.4 System Tray Lifecycle
- System tray initialized in `src-tauri/src/lib.rs` using Tauri 2 tray icon builder.
- Tray tooltip: `"AeroGuard — Counter-UAS Defensive Operations"`.
- Menu Items:
  - `"Open Operator Console"`: Shows, unminimizes, and focuses the main window.
  - `"Quit AeroGuard"`: Exits the application process (`app.exit(0)`).
- Left-click on tray icon automatically restores and focuses the existing window.

---

## 4. Security Configuration

### 4.1 Content Security Policy (CSP)
Defined in `src-tauri/tauri.conf.json`:
```text
default-src 'self';
script-src 'self';
style-src 'self' 'unsafe-inline';
connect-src 'self' http://127.0.0.1:8000 http://localhost:8000 ws://127.0.0.1:8000 ws://localhost:8000;
img-src 'self' data: blob:;
```

### 4.2 Capability Permissions
Defined in `src-tauri/capabilities/default.json`:
```json
{
  "identifier": "default",
  "windows": ["main"],
  "permissions": [
    "core:default",
    "notification:default"
  ]
}
```
- **Strictly Denied**: Shell execution, filesystem access, child process execution, arbitrary network fetching, token/credential storage.

---

## 5. Build & Packaging Verification

### 5.1 Verification Commands
- **Frontend Unit Tests**: `npm test` → **155 passed** (0 failures).
- **Frontend Typecheck**: `npm --prefix apps/operator run typecheck` → **0 errors**.
- **Frontend Web Build**: `npm --prefix apps/operator run build` → **PASS** (`dist/` generated).
- **Backend Tests**: `pytest -v` → **145 passed** (0 regressions).
- **Rust Cargo Check**: `cargo check --manifest-path src-tauri/Cargo.toml` → **PASS** (0 errors).
- **Rust Cargo Tests**: `cargo test --manifest-path src-tauri/Cargo.toml` → **PASS** (0 errors).
- **Desktop Production Build**: `npm run build:desktop` → **PASS** (Finished 2 bundles).

### 5.2 Generated Distributable Artifacts
| Artifact Type | File Path | Size | Description |
|---|---|---|---|
| **Standalone Binary** | `src-tauri/target/release/aeroguard-desktop.exe` | 9.32 MB | Direct executable binary for Windows x64. |
| **MSI Installer** | `src-tauri/target/release/bundle/msi/AeroGuard_0.1.0_x64_en-US.msi` | 3.04 MB | Enterprise Windows Installer package (WiX 3.14). |
| **NSIS Setup** | `src-tauri/target/release/bundle/nsis/AeroGuard_0.1.0_x64-setup.exe` | 2.04 MB | Self-contained Windows setup installer (NSIS 3.11). |

---

## 6. Git Checkpoint History
- `8178761 feat: establish tauri desktop foundation` (Checkpoint UI8-A)
- `45b431d feat: integrate tauri desktop environment bridge` (Checkpoint UI8-B)
- `75291d8 feat: add native notifications and system tray` (Checkpoint UI8-C)
- `[Pending] feat: finalize tauri desktop packaging` (Checkpoint UI8-D)
