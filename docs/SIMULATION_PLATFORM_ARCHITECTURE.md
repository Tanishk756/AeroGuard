# AeroGuard Simulation & Digital-Twin Platform Architecture Specification
## Target Architecture for Complete UAV/Robotics Simulation, Hardware Registry, and Telemetry Engine

---

## 1. Executive Summary & Product Vision

AeroGuard is evolving from a counter-UAS situational-awareness platform into a **Complete UAV/Robotics Simulation & Digital-Twin Engineering Workstation**. The platform empowers aerospace, robotics, and defense engineers to design vehicle airframes, select avionics/propulsion/sensor hardware components, configure environmental physics and sensor noise, run Software-in-the-Loop (SITL) and Hardware-in-the-Loop (HIL) simulations, conduct parameter-sweep experiments, and analyze high-frequency telemetry and replay runs.

The platform architecture guarantees **SITL / HIL / Real-Hardware Parity**: the exact same vehicle definition, control plane API, telemetry pipeline, and workstation UI operate seamlessly whether connected to Gazebo/SITL, a physical HIL testbed, or live operational vehicle telemetry.

---

## 2. Current vs Target Architecture Comparison

| Architectural Dimension | Current AeroGuard Stack (PR1–PR4) | Target AeroGuard Simulation Stack |
| :--- | :--- | :--- |
| **Primary Focus** | Counter-UAS tracking, incident management, API security | Complete UAV engineering laboratory & digital-twin simulation |
| **Simulation Core** | In-memory synthetic trajectory & detection generator | Multi-engine orchestrator (Gazebo Harmonic, ArduPilot SITL, PX4 SITL) |
| **Vehicle Model** | Hardcoded target tracks & basic modal parameters | Hierarchical component-based vehicle schema (Airframe, FC, Motors, ESCs, Sensors) |
| **Hardware Registry** | Static synthetic sensor definitions | Dynamic Component Library (motors, batteries, GNSS, IMUs, LiDARs, companion computers) |
| **Telemetry Transport** | Basic JSON WebSocket detection feed | Normalized `VehicleState` telemetry pipeline (MAVLink, ROS 2, Serial, WebSocket) |
| **Desktop Workstation** | Tauri wrapper around React web console | Process-orchestrating workstation managing local SITL, Gazebo, and ROS 2 bridges |
| **Analytics & Experiments**| PostgreSQL query aggregations | DuckDB / Apache Arrow high-frequency run recording & parameter sweep experiments |

---

## 3. Core Architecture Topology & Layering

AeroGuard is structured into 5 decoupled architectural layers:

```
+-----------------------------------------------------------------------------------+
|                        LAYER 5 — OPERATOR WORKSTATION UI                          |
|  (React, TypeScript, WebGL/WebGPU 3D Simulation View, Vehicle Builder, Telemetry) |
+-----------------------------------------+-----------------------------------------+
                                          | WSS / HTTP REST
+-----------------------------------------v-----------------------------------------+
|                        LAYER 1 — AEROGUARD CONTROL PLANE                          |
|  (FastAPI Backend, Projects, Users, Scenarios, Hardware Registry, Experiments)    |
+-----------------------------------------+-----------------------------------------+
                                          | Internal Bus / Process Manager
+-----------------------------------------v-----------------------------------------+
|                     LAYER 2 — SIMULATION ORCHESTRATOR ENGINE                      |
|  (Lifecycle Watchdog, Process Spawner, Failure Injector, Run Recorder)            |
|                                                                                   |
|  +---------------------+  +----------------------+  +-------------------------+  |
|  | GazeboAdapter       |  | ArduPilotSITLAdapter |  | PX4SITLAdapter          |  |
|  +---------------------+  +----------------------+  +-------------------------+  |
+-----------------------------------------+-----------------------------------------+
                                          | MAVLink / ROS 2 / Serial
+-----------------------------------------v-----------------------------------------+
|                   LAYER 3 — TELEMETRY & TRANSPORT NORMALIZER                      |
|  (MAVLink UDP/TCP, ROS 2 MicroXRCE-DDS, Serial Bridge -> VehicleState Broadcast)   |
+-----------------------------------------+-----------------------------------------+
                                          | Physics / SITL / HIL Execution
+-----------------------------------------v-----------------------------------------+
|                  LAYER 4 — SIMULATORS & AUTOPILOT RUNTIMES                        |
|  (Gazebo Harmonic, ArduPilot sim_vehicle, PX4 Autopilot SITL, HIL Testbed)        |
+-----------------------------------------------------------------------------------+
```

---

## 4. Architectural Module Boundaries

```
[Vehicle Builder UI] ----> [Vehicle Model Compositor] ----> [Hardware Registry]
                                     |
                                     v (Validates Specs & Electrical Budget)
                            [Simulation Scenario]
                                     |
                                     v
                        [Simulation Orchestrator]
                         /           |          \
                        v            v           v
           [Gazebo Adapter] [SITL Adapter] [Failure Injector]
                        \            |          /
                         v           v         v
                      [Telemetry Transport Normalizer]
                                     |
                                     v
                     [Normalized VehicleState Pipeline]
                        /            |          \
                       v             v           v
           [Workstation UI]  [DuckDB Run Recorder]  [EventBus]
```

---

## 5. Comprehensive Data Model Schema

### Core Entities & Relationships

```
Project (1) <--- (N) SimulationScenario (1) <--- (N) SimulationRun (1) ---> (1) SimulationArtifact
   |                       |
   v (1)                   v (1)
VehicleConfiguration (1) -> Vehicle (1) ---> (N) Component
                                              (Motors, ESCs, FC, GNSS, IMU, LiDAR)
```

#### Entity Definitions:
1. `Project`: Top-level workspace for an engineering program or research team.
2. `Vehicle`: Canonical vehicle entity (e.g. "AeroGuard Quad-X Recon").
3. `VehicleConfiguration`: Immutable snapshot of a vehicle's component topology, masses, aerodynamics, and firmware settings.
4. `Component`: Individual hardware component (e.g. "T-Motor MN2212", "Cube Orange+", "Holybro Micro M8N").
5. `HardwareSpecification`: Detailed datasheets, electrical specs (KV, voltage, max current), physical dimensions, and simulation noise parameters.
6. `Firmware`: Autopilot firmware specification (ArduPilot Copter 4.5.1, PX4 v1.14.0).
7. `Simulator`: Simulation engine spec (Gazebo Harmonic 8.0, ArduPilot SITL, Custom FDM).
8. `SimulationScenario`: Complete, reproducible simulation configuration (Vehicle, Environment, Weather, Failures, Mission, Seeds).
9. `SimulationRun`: Single execution instance of a scenario.
10. `SimulationArtifact`: High-frequency telemetry log, DuckDB parquet recording, video capture, and diagnostic output.
11. `World`: Terrain mesh, obstacles, weather bounds, and Gazebo SDF world definitions.
12. `EnvironmentConfiguration`: Wind vector, temperature, air density, barometric baseline, solar/magnetic index.
13. `SensorConfiguration`: Per-sensor noise model (Gaussian noise, bias, drift, dropouts, latency).
14. `CommunicationLink`: Telemetry link parameters (baudrate, packet loss %, latency ms, bandwidth limit).
15. `Mission`: Simulator-neutral waypoint, loiter, takeoff, land, and survey plan.
16. `Experiment`: Parameter-sweep execution definition (e.g., test 3 battery capacities across 5 wind speeds).
17. `ExperimentRun`: Individual run belonging to a parameter-sweep experiment.
18. `TelemetryStream`: Live websocket / MAVLink telemetry channel.
19. `TelemetrySample`: High-frequency state vector sample (`VehicleState`).
20. `Event`: Discrete simulation event (e.g., `MOTOR_2_FAILURE`, `GPS_LOCK_LOST`, `WAYPOINT_3_REACHED`).
21. `FailureScenario`: Programmed schedule of fault injections.
22. `ReplaySession`: Time-synced playback controller instance.

---

## 6. Simulation Engine Lifecycle State Machine

```
               +---------+
               | CREATED |
               +----+----+
                    | Provision (Spawn Gazebo / SITL)
                    v
             +--------------+
             | PROVISIONED  |
             +----+---------+
                  | Start Simulation
                  v
              +---------+        Pause        +--------+
              | RUNNING | ------------------> | PAUSED |
              +----+----+ <------------------ +----+---+
                   |           Resume              |
                   | Stop / Complete               | Stop
                   v                               v
              +---------+                     +--------+
              | STOPPED | <------------------ | FAILED |
              +----+----+                     +--------+
                   | Finalize Recording & Artifacts
                   v
             +------------+
             | RECORDED   |
             +------------+
```

---

## 7. Digital Twin / Vehicle Model Composition

Every vehicle model is strictly composed of modular, interchangeable components:

```
Vehicle Digital Twin
 ├── Airframe (Multirotor / Fixed-Wing / VTOL / Rover)
 ├── Flight Controller (Cube Orange+, Pixhawk 6X, Matek H743)
 ├── Firmware (ArduPilot / PX4 + parameters)
 ├── Propulsion System
 │    ├── Motors (KV, Resistance, Idle Current, Max Current, Mass)
 │    ├── ESCs (Max Voltage, Protocol DShot/PWM, Response Delay)
 │    └── Propellers (Diameter, Pitch, Thrust Coeff, Drag Coeff)
 ├── Power System
 │    ├── Battery (Chemistry LiPo/LiIon, Cells S, Capacity mAh, Max C-Rating)
 │    ├── BEC / Power Module (Voltage Regulation, Current Sense Scale)
 │    └── Power Distribution Board
 ├── Navigation & Avionics
 │    ├── GNSS (GPS/GLONASS, Update Hz, Noise StdDev m, Latency)
 │    ├── IMU (Accel/Gyro Noise Density, Random Walk, Bias Drift)
 │    ├── Magnetometer (Declination, Noise, Iron Distortion Model)
 │    └── Barometer (Altitude Noise m, Thermal Drift)
 ├── Perception Payloads
 │    ├── Cameras (Resolution, FOV, FPS, Sensor Model, Noise)
 │    ├── LiDAR (Channels, Range m, Scan Rate Hz, Angular Res)
 │    ├── Rangefinders (Laser/Sonar, Min/Max Range, Noise)
 │    └── Optical Flow (Update Rate, Min Light Threshold)
 ├── Communications
 │    ├── Telemetry Radio (Frequency, Transmit Power, Range, Packet Loss Model)
 │    ├── RC Link (Protocol SBUS/CRSF, Channel Count, FailSafe Timeout)
 │    └── Companion Computer Network (Ethernet / WiFi / Serial)
 └── Companion Computer (Jetson Orin Nano, Raspberry Pi 5)
```

---

## 8. Hardware Component Registry

The Hardware Registry provides a curated library of real-world components and allows users to register custom components.

### Spec Schema Example: Brushless Motor
```json
{
  "component_id": "mot-tmotor-mn2212-920",
  "category": "MOTOR",
  "manufacturer": "T-Motor",
  "model": "MN2212",
  "variant": "920KV",
  "physical": { "mass_grams": 55.0, "diameter_mm": 27.5, "length_mm": 30.0 },
  "electrical": { "kv": 920, "max_current_a": 18.0, "max_voltage_v": 16.8, "resistance_ohm": 0.115 },
  "simulation": { "torque_constant_kt": 0.0104, "rotor_inertia_kgm2": 1.2e-5 },
  "datasheet_url": "https://specs.aeroguard.internal/motors/mn2212.pdf"
}
```

---

## 9. Simulator Adapter Architecture (`BaseSimulatorAdapter`)

```python
class BaseSimulatorAdapter(ABC):
    @abstractmethod
    async def provision(self, scenario: SimulationScenario) -> bool: ...
    @abstractmethod
    async def start(self) -> bool: ...
    @abstractmethod
    async def pause(self) -> bool: ...
    @abstractmethod
    async def resume(self) -> bool: ...
    @abstractmethod
    async def stop(self) -> bool: ...
    @abstractmethod
    async def step(self, ticks: int = 1) -> bool: ...
    @abstractmethod
    async def inject_failure(self, failure: FailureScenario) -> bool: ...
    @abstractmethod
    async def get_telemetry(self) -> VehicleState: ...
```

Supported Implementations:
- `GazeboHarmonicAdapter`: Communicates over Gazebo Transport / ROS 2 topics.
- `ArduPilotSITLAdapter`: Manages `sim_vehicle.py` / `arducopter` binary & MAVLink ports.
- `PX4SITLAdapter`: Manages `px4` binary & uORB / MicroXRCE-DDS bridge.
- `HILAdapter`: Interfaces with physical Flight Controller over USB Serial / Ethernet.

---

## 10. Autopilot & Telemetry Transport Abstraction

Telemetry data is normalized into a unified schema (`VehicleState`) before reaching the UI or analytics engines.

### Normalized `VehicleState` Schema
```typescript
interface VehicleState {
  timestamp_utc: string;
  sim_time_seconds: number;
  vehicle_id: string;
  flight_mode: string; // e.g. "GUIDED", "AUTO", "RTL", "STABILIZE"
  armed: boolean;
  position: { latitude: number; longitude: number; altitude_msl: number; altitude_relative: number };
  velocity: { vx: number; vy: number; vz: number; ground_speed: number };
  attitude: { roll_deg: number; pitch_deg: number; yaw_deg: number };
  angular_velocity: { roll_rate: number; pitch_rate: number; yaw_rate: number };
  battery: { voltage_v: number; current_a: number; remaining_percent: number; consumed_mah: number };
  gps: { fix_type: number; satellites_visible: number; hdop: number; vdop: number };
  link_status: { rssi_dbm: number; packet_loss_percent: number; latency_ms: number };
  sensor_health: Record<string, boolean>; // e.g. { imu1: true, mag1: true, lidar: false }
}
```

---

## 11. Desktop Process Architecture (Tauri / Local-First Engine)

```
+--------------------------------------------------------------------------+
|                            TAURI DESKTOP WINDOW                          |
|                        (React Operator Console UI)                       |
+------------------------------------+-------------------------------------+
                                     | IPC Commands
+------------------------------------v-------------------------------------+
|                         RUST TAURI CORE PROCESS                          |
|  (Local Process Manager, Subprocess Watchdog, Native Binary Finder)      |
+--------+---------------------------+----------------------------+--------+
         |                           |                            |
         v (Subprocess)              v (Subprocess)               v (Subprocess)
+------------------+       +--------------------+       +------------------+
| Gazebo Harmonic  |       | ArduPilot SITL     |       | MAVLink / ROS 2  |
| Physics Server   |       | Binary (arducopter)|       | Local Bridge     |
+------------------+       +--------------------+       +------------------+
```

---

## 12. Experiment Framework & Parameter Sweeps

AeroGuard enables multi-run automated testing:

```
Experiment Definition: "Wind Resistance vs Battery Flight Time"
├── Sweep Variables:
│     - Battery Capacity: [4000 mAh, 5000 mAh, 6000 mAh]
│     - Wind Velocity: [0 m/s, 5 m/s, 10 m/s, 15 m/s]
├── Repetitions per combination: 3
└── Total Automated Runs: 3 * 4 * 3 = 36 Simulation Runs
```
Each run automatically logs telemetry to DuckDB Parquet files, allowing instant cross-run comparison charts in the UI.

---

## 13. Security & Defensive Boundaries

- **Strict Research Scope**: Zero weapon engagement, targeting, kinetic action, or offensive countermeasure functionality (`AGENTS.md` enforced).
- **Failure Injection Isolation**: Fault injections (motor cut, GPS spoofing, packet loss) exist **strictly inside the local simulation sandbox**.
- **Credentials & API Safety**: Telemetry streams and configuration exports are sanitized against credential leaks.
