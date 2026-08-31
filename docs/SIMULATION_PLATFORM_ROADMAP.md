# AeroGuard Simulation & Digital-Twin Platform Roadmap
## Master Multi-Phase Engineering Roadmap (Phases S0 through S12)

---

## Roadmap Executive Summary

This roadmap defines the multi-phase engineering progression required to build the AeroGuard UAV/Robotics Simulation and Digital-Twin Platform. Each phase builds incrementally on top of previous work without breaking existing production APIs, security controls, or test suites.

```
[Phase S0: Architecture & Foundation]
               │
               ▼
[Phase S1: Core Abstraction Engine] ────► [Phase S3: Hardware Registry & Vehicle Builder]
               │                                       │
               ▼                                       ▼
[Phase S2: Gazebo Integration] ─────────► [Phase S4: ArduPilot SITL Integration]
               │                                       │
               ▼                                       ▼
[Phase S5: PX4 SITL Integration] ────────► [Phase S6: Scenario & World Builder]
                                                       │
                                                       ▼
[Phase S8: Mission & Experiments] ◄────── [Phase S7: Simulation Workstation UI]
               │
               ▼
[Phase S9: Replay & Log Analytics] ─────► [Phase S10: HIL Hardware Integration]
                                                       │
                                                       ▼
[Phase S12: Cloud Sync & Fleet] ◄──────── [Phase S11: Real Hardware Telemetry]
```

---

## Phase Breakdown Specifications

### Phase S0 — Architecture & Repository Restructuring Plan
- **Objective**: Establish platform architecture specifications, simulation domain models, and adapter contracts without modifying production source code.
- **Deliverables**: Architectural audit, roadmap, Phase S0 implementation plan.
- **Acceptance Criteria**: All 3 planning documents approved.

---

### Phase S1 — Simulation Core Abstraction
- **Objective**: Implement base class interfaces for `BaseSimulatorAdapter`, `BaseAutopilotAdapter`, `SimulationOrchestrator`, and normalized `VehicleState` models.
- **Modules**: `backend/app/simulation/core/`, `backend/app/schemas/simulation_platform.py`.
- **APIs**: `POST /api/v1/simulation/sessions`, `GET /api/v1/simulation/sessions/{id}/telemetry`.
- **Database**: Add `simulation_scenarios`, `simulation_runs`, `vehicle_configurations` tables via Migration 0017.
- **Tests**: Pytest unit tests for orchestrator lifecycle state transitions and adapter mocks.

---

### Phase S2 — Gazebo Integration
- **Objective**: Build `GazeboHarmonicAdapter` for Gazebo 8 physics server management and ROS 2 transport bridge.
- **Modules**: `backend/app/simulation/adapters/gazebo.py`, `backend/app/simulation/sdf/`.
- **Dependencies**: Gazebo Harmonic, ROS 2 Jazzy.
- **Tests**: Gazebo SDF generator unit tests and process lifecycle contract tests.

---

### Phase S3 — Hardware Registry & Vehicle Builder
- **Objective**: Implement dynamic Component Library (motors, batteries, FCs, sensors) and Vehicle Compositor UI with electrical/mass budget calculations.
- **Modules**: `backend/app/hardware/`, `apps/operator/src/components/vehicle/`.
- **APIs**: `GET /api/v1/hardware/components`, `POST /api/v1/vehicles`.
- **UI Changes**: Add VEHICLE BUILDER and HARDWARE LIBRARY workspaces.
- **Tests**: Electrical current/voltage budget validation tests.

---

### Phase S4 — ArduPilot SITL Integration
- **Objective**: Build `ArduPilotSITLAdapter` managing `sim_vehicle.py` / `arducopter` binary and MAVLink UDP/TCP socket transport.
- **Modules**: `backend/app/simulation/adapters/ardupilot.py`, `backend/app/telemetry/mavlink.py`.
- **Dependencies**: `pymavlink`, ArduPilot SITL.
- **Tests**: MAVLink message parser unit tests and SITL process spawner tests.

---

### Phase S5 — PX4 SITL Integration
- **Objective**: Build `PX4SITLAdapter` managing `px4` binary and uORB / MicroXRCE-DDS bridge.
- **Modules**: `backend/app/simulation/adapters/px4.py`.
- **Dependencies**: PX4 Autopilot SITL, MicroXRCE-DDS Agent.

---

### Phase S6 — Scenario & World Builder
- **Objective**: Build visual Scenario Builder UI supporting weather, wind vectors, terrain meshes, obstacles, and failure schedule configuration.
- **Modules**: `apps/operator/src/components/scenario/`, `backend/app/simulation/environment.py`.

---

### Phase S7 — Telemetry & Simulation Workstation UI
- **Objective**: Evolve Operator UI into a 3D Simulation Workstation with WebGL/WebGPU 3D viewport, attitude indicator, flight gauges, and simulation controls.
- **Modules**: `apps/operator/src/components/workstation/`, `apps/operator/src/services/telemetryStream.ts`.

---

### Phase S8 — Mission & Experiment Framework
- **Objective**: Implement simulator-neutral mission waypoint planner and automated parameter sweep experiment engine (e.g. test 3 batteries across 4 wind speeds).
- **Modules**: `backend/app/experiments/`, `apps/operator/src/components/experiments/`.

---

### Phase S9 — Replay & Log Analytics
- **Objective**: High-frequency telemetry log recording to DuckDB Parquet artifacts with time-synced playback and multi-run comparison charts.
- **Modules**: `backend/app/analytics/duckdb_store.py`, `apps/operator/src/components/replay/`.

---

### Phase S10 — Hardware-in-the-Loop (HIL) Integration
- **Objective**: Physical Flight Controller HIL bridge over USB Serial / Ethernet with real sensor emulation injection.
- **Modules**: `backend/app/simulation/adapters/hil.py`.

---

### Phase S11 — Real Hardware Telemetry Integration
- **Objective**: Live operational vehicle telemetry stream ingestion via MAVLink / ROS 2 without changing UI models.
- **Modules**: `backend/app/telemetry/real_hardware.py`.

---

### Phase S12 — Cloud Collaboration & Fleet Management
- **Objective**: Multi-user project synchronization, cloud S3 run artifact archive, and fleet performance metrics.
- **Modules**: `backend/app/cloud/sync.py`.

---

## Verification & Acceptance Criteria per Phase
Every phase requires:
1. **Backend**: Pytest suite 100% PASS (`pytest backend/tests`).
2. **Frontend**: Vitest suite 100% PASS (`npm --prefix apps/operator test`), zero TS errors (`typecheck`), Vite build PASS (`build`).
3. **Desktop**: Cargo check & test 100% PASS (`cargo check`, `cargo test`).
4. **CI/CD**: GitHub Actions workflow 100% GREEN.
