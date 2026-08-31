# AeroGuard Simulation Core v0.1 Implementation Plan
## First Vertical Slice: Quad-X + Gazebo Harmonic + ArduPilot SITL + Telemetry Workstation + Recording & Replay

---

## 1. Goal Description

Implement the first complete vertical slice of the AeroGuard Simulation Core (v0.1). This milestone proves end-to-end integration between AeroGuard's Control Plane, Simulation Orchestrator, Gazebo Harmonic, ArduPilot SITL, MAVLink transport, normalized telemetry pipeline, and React 3D Simulation Workstation.

---

## 2. End-to-End User Flow (v0.1 Milestone)

```
[OPEN AEROGUARD WORKSTATION]
            │
            ▼
   [CREATE PROJECT] -> "AeroGuard Quad-X Evaluation"
            │
            ▼
   [CREATE VEHICLE] -> Select "Generic Quadrotor", "ArduPilot Copter", "Quad-X Frame"
            │
            ▼
  [CREATE SCENARIO] -> Select "Gazebo Harmonic Engine", "Empty Grassland World"
            │
            ▼
 [START SIMULATION] -> Orchestrator provisions Gazebo & ArduPilot SITL
            │
            ▼
[TELEMETRY DISPLAY] -> Workstation renders live 3D orientation, position, attitude, velocity, battery
            │
            ▼
[SIMULATION CONTROL]-> User triggers PAUSE / RESUME / STOP
            │
            ▼
   [RUN RECORDING]  -> Telemetry recorded to DuckDB Parquet artifact
            │
            ▼
   [RUN REPLAY]     -> User replays simulation run with time-seeking controls
```

---

## 3. Proposed Component Changes

### Component 1: Core Schemas & Data Contracts (`backend/app/schemas/`)
- `[NEW] backend/app/schemas/simulation_platform.py`: Pydantic models for `VehicleModelConfig`, `HardwareComponentSpec`, `SimulationScenarioSpec`, `VehicleStateVector`, `SimulationRunArtifact`.

### Component 2: Simulation Orchestrator & Adapters (`backend/app/simulation/`)
- `[NEW] backend/app/simulation/core/base_adapter.py`: Abstract base classes `BaseSimulatorAdapter` and `BaseAutopilotAdapter`.
- `[NEW] backend/app/simulation/core/orchestrator.py`: Thread-safe `SimulationOrchestrator` managing process lifecycle, state machine, and error watchdog.
- `[NEW] backend/app/simulation/adapters/gazebo.py`: `GazeboHarmonicAdapter` managing Gazebo process, SDF world generation, and transport bridge.
- `[NEW] backend/app/simulation/adapters/ardupilot.py`: `ArduPilotSITLAdapter` managing `sim_vehicle.py` / `arducopter` binary, MAVLink UDP ports (14550/14551), and parameter files.

### Component 3: Telemetry Normalizer & Transport (`backend/app/telemetry/`)
- `[NEW] backend/app/telemetry/mavlink_normalizer.py`: MAVLink message parser converting `ATTITUDE`, `GLOBAL_POSITION_INT`, `VFR_HUD`, `SYS_STATUS`, `GPS_RAW_INT` into normalized `VehicleState` dicts.

### Component 4: REST & WebSocket API Routes (`backend/app/api/v1/routes/`)
- `[NEW] backend/app/api/v1/routes/simulation_platform.py`:
  - `POST /api/v1/simulation/scenarios` (Create scenario)
  - `POST /api/v1/simulation/runs/start` (Start simulation)
  - `POST /api/v1/simulation/runs/{run_id}/pause` (Pause simulation)
  - `POST /api/v1/simulation/runs/{run_id}/resume` (Resume simulation)
  - `POST /api/v1/simulation/runs/{run_id}/stop` (Stop simulation)
  - `GET /api/v1/simulation/runs/{run_id}/telemetry` (Get run telemetry history)
  - `WS /api/v1/simulation/runs/{run_id}/stream` (Real-time WSS telemetry broadcast)

### Component 5: Operator Workstation UI (`apps/operator/src/`)
- `[NEW] apps/operator/src/components/workstation/SimulationWorkstation.tsx`: 3D simulation workstation with Three.js / Canvas 3D viewport, flight gauges, telemetry panel, and control bar.
- `[NEW] apps/operator/src/services/telemetryStream.ts`: WebSocket client parsing `VehicleState` messages.

### Component 6: Test Suite (`backend/tests/`)
- `[NEW] backend/tests/test_simulation_platform_v01.py`: Integration test suite validating orchestrator lifecycle, adapter contract mocks, MAVLink normalization, and REST endpoints.

---

## 4. Required Local Software & Environment

| Dependency | Classification | Windows Local Path / Method | WSL2 / Linux Path |
| :--- | :--- | :--- | :--- |
| **Python 3.12** | `LOCAL VERIFIED` | `.venv/Scripts/python` | `/usr/bin/python3` |
| **FastAPI / Pytest** | `LOCAL VERIFIED` | `pytest backend/tests` | `pytest` |
| **Node.js / React** | `LOCAL VERIFIED` | `npm --prefix apps/operator` | `npm` |
| **Tauri / Rust** | `LOCAL VERIFIED` | `cargo check --manifest-path src-tauri/Cargo.toml` | `cargo` |
| **Gazebo Harmonic 8** | `WSL / LINUX REQUIRED` | WSL2 Ubuntu 24.04 (`gz sim`) | Linux native (`gz sim`) |
| **ArduPilot SITL** | `WSL / LINUX REQUIRED` | WSL2 Ubuntu 24.04 (`sim_vehicle.py`) | Linux native (`sim_vehicle.py`) |
| **MAVLink / pymavlink** | `LOCAL VERIFIED` | `pip install pymavlink` | `pip install pymavlink` |

---

## 5. Verification & Test Plan

1. **Backend Tests**: Run `pytest backend/tests` -> Must pass 100% with 0 failures.
2. **Frontend Tests**: Run `npm --prefix apps/operator test`, `typecheck`, and `build` -> Zero TS errors.
3. **Desktop Tests**: Run `cargo check` and `cargo test` -> Zero Rust errors.
4. **Adapter Contract Mocks**: Mock Gazebo and SITL processes when running on Windows host where Gazebo binary is uninstantiated.
