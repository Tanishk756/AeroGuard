# Stage S9: PX4 Autopilot SITL Integration & Multi-Autopilot Abstraction Report

## Executive Summary

Stage S9 establishes a multi-autopilot hardware abstraction layer for AeroGuard, decoupling simulation and mission execution logic from specific flight controller firmware. The platform seamlessly supports both **ArduPilot (ArduCopter)** and **PX4 Autopilot**.

## Architectural Design

```
                     Scenario / Vehicle Digital Twin
                                   │
                                   ▼
                       BaseAutopilotAdapter
                                   │
         ┌─────────────────────────┴─────────────────────────┐
         ▼                                                   ▼
ArduPilotSITLAdapter                                PX4AutopilotAdapter
 (MAVLink UDP 14550)                                (MAVLink UDP 14540)
  STABILIZE, GUIDED,                                 POSCTL, AUTO.MISSION,
  AUTO, RTL, LAND                                    OFFBOARD, AUTO.RTL, AUTO.LAND
         │                                                   │
         └─────────────────────────┬─────────────────────────┘
                                   ▼
                         MissionTranslator
                  (MAVLink Command Encoding)
                                   │
                                   ▼
                        Normalized VehicleState
```

## Autopilot Readiness & Environment Diagnostics

- Host/WSL SITL binaries are automatically inspected via `SimulationProcessManager.get_capabilities()`.
- ArduPilot SITL status: Inspected via PATH / WSL / `AEROGUARD_ARDUPILOT_SITL_PATH`.
- PX4 SITL status: Inspected via PATH / WSL / `AEROGUARD_PX4_SITL_PATH`.
- When SITL toolchains are not installed in the host environment, the adapters operate in deterministic mock boundary mode for testing, clearly recording `environment_blocked=True` without fabricating fake binary executions.

## Mission Translation Matrix

| Unified Mission Item | ArduPilot MAVLink Mapping | PX4 MAVLink Mapping |
| :--- | :--- | :--- |
| `TAKEOFF` | `MAV_CMD_NAV_TAKEOFF` (22), `z_alt` | `MAV_CMD_NAV_TAKEOFF` (22), `param7_alt`, `param1` pitch |
| `WAYPOINT` | `MAV_CMD_NAV_WAYPOINT` (16), `x_lat`, `y_lon`, `z_alt` | `MAV_CMD_NAV_WAYPOINT` (16), `param5_lat`, `param6_lon`, `param7_alt` |
| `LOITER` | `MAV_CMD_NAV_LOITER_TIME` (19), `param1` time | `MAV_CMD_NAV_LOITER_TIME` (19), `param1` time |
| `LAND` | `MAV_CMD_NAV_LAND` (21) | `MAV_CMD_NAV_LAND` (21) |
| `RETURN_TO_HOME` | `MAV_CMD_NAV_RETURN_TO_LAUNCH` (20) | `MAV_CMD_NAV_RETURN_TO_LAUNCH` (20) |
