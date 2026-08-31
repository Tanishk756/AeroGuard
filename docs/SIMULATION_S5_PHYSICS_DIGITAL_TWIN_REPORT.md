# AeroGuard Stage S5 Physics-Based Vehicle Assembly & Real Hardware-to-Gazebo Digital Twin Report

## 1. Executive Summary
Stage S5 establishes the physics-based digital twin compilation pipeline in AeroGuard. Selected hardware components (Frame, Motor, ESC, Propeller, Battery, Flight Controller, GPS) are compiled deterministically into a first-order rigid-body physical model (`CompiledVehicleModel`) with explicit property provenance (`HARDWARE_SPEC`, `ESTIMATED`, `USER_DEFINED`, `SIMULATOR_GENERATED`). The compiler generates Gazebo Harmonic 8.15 XML SDF 1.9 files dynamically, freezes immutable simulation run snapshots in isolated directories (`.aeroguard/simulations/<run-id>/`), and provides motor failure injection.

---

## 2. Architectural Compilation & Execution Chain

```
    [Hardware Registry Catalog]
               │
               ▼ (PersistentVehicle)
   [VehicleAssemblyCompiler] ───► Calculates: Mass, COM (x,y,z), 3D Inertia Tensor (Ixx,Iyy,Izz),
               │                               Wheelbase, Arm Length, Propulsion Dynamics, Battery Wh & Runtime
               ▼
     [CompiledVehicleModel] (SHA256 Hash + Property Provenance Tags)
               │
               ├──► [SimulationSnapshotManager] ──► Freezes .aeroguard/simulations/<run-id>/
               │                                      (vehicle.sdf, world.sdf, configuration.json, manifest.json)
               ▼
    [GazeboVehicleGenerator]
               │
               ▼ (XML SDF 1.9)
    [Gazebo Harmonic 8.15.0] ◄──► [ArduCopter 4.6.0 SITL] ◄──► [MAVLink Transport] ──► [VehicleState Telemetry]
```

---

## 3. Subsystem Classification Matrix

| Subsystem Component | Target Framework | Empirical Status | Verification Rationale |
| :--- | :--- | :--- | :--- |
| **VehicleAssemblyCompiler** | Python / Pydantic | `LOCAL VERIFIED` | Deterministic SHA256 hashing & provenance tagging verified |
| **RigidBodyPhysicsEngine** | Python / NumPy | `LOCAL VERIFIED` | Mass, COM, and 3D moments of inertia tensor ($I_{xx}, I_{yy}, I_{zz}$) calculated |
| **PropulsionEngine** | Python Core | `ESTIMATED` | First-order RPM, max thrust, torque, T/W ratio & hover throttle calculated |
| **BatteryEnergyEngine** | Python Core | `ESTIMATED` | Stored Wh, hover power W, hover current A, and runtime min calculated |
| **GazeboVehicleGenerator** | Gazebo Harmonic 8.15 | `LOCAL VERIFIED` | Dynamic SDF 1.9 XML generation with multicopter motor model plugins verified |
| **SimulationSnapshotManager**| Python / SQLAlchemy | `LOCAL VERIFIED` | Isolated artifact directory creation & database snapshot freezing verified |
| **SimulationFailureInjector**| Python Core | `LOCAL VERIFIED` | Motor failure injection event dispatch verified |
| **Gazebo 8.15.0 & SITL 4.6.0**| Linux / WSL2 | `LIVE VERIFIED` | Live execution pipeline with pymavlink UDP transport verified |

---

## 4. Verification & Regression Metrics
- **Backend Pytest Suite**: 734 passed, 7 skipped (100% pass rate).
- **Frontend Node Test Runner**: 357 passed (100% pass rate).
- **TypeScript Typecheck**: Zero errors (`tsc --noEmit`).
- **Vite Production Build**: Clean build (`dist/`).
- **Desktop Tauri Suite**: Zero Rust compilation or test errors.
- **Git Hygiene**: Clean formatting (`git diff --check`).
