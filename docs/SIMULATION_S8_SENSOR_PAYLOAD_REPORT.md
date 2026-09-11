# Stage S8: Sensor & Payload Digital Twin Engineering Report

## Executive Summary

Stage S8 expands AeroGuard's vehicle digital twin architecture by incorporating hardware-accurate Sensor Instances (`IMU`, `GPS`, `RANGEFINDER`, `CAMERA`) and Payload Attachments (`CAMERA_PAYLOAD`, `LIDAR_PAYLOAD`, `GENERIC_PAYLOAD`).

The spatial placement $(x, y, z)$ and mass of mounted sensors and payloads dynamically alter:
1. Vehicle total mass ($m_{\text{total}}$)
2. 3D Center of Mass location ($\vec{r}_{\text{com}}$)
3. Central rigid-body moment of inertia tensor ($I_{xx}, I_{yy}, I_{zz}$)
4. Total non-propulsion power budget ($P_{\text{avionics}} + P_{\text{sensors}} + P_{\text{payloads}}$)
5. Gazebo Harmonic 8.15 SDF 1.9 dynamic sensor XML generation
6. Sensor failure injection capability (`GPS` dropout, `IMU` noise spike)

## Architectural Design

```
Hardware Registry / Vehicle Twin
       │
       ├── Sensor Instances (IMU, GPS, LiDAR, Camera)
       └── Payload Attachments (EO/IR Gimbal Camera, 3D LiDAR Scanner)
               │
               ▼
   RigidBodyPhysicsEngine
  (Mass, CoM Shift, Inertia)
               │
               ├── BatteryEnergyEngine (Power Budget: Avionics + Sensors + Payloads)
               └── GazeboSensorGenerator (SDF 1.9 XML Tags)
                       │
                       ▼
       Dynamic Simulation Telemetry & Fault Injection
```

## Schema & API Endpoints

- `POST /api/v1/vehicles/{id}/sensors` — Add mounted sensor instance
- `GET /api/v1/vehicles/{id}/sensors` — List vehicle sensor instances
- `DELETE /api/v1/vehicles/{id}/sensors/{sensor_id}` — Detach sensor instance
- `POST /api/v1/vehicles/{id}/payloads` — Add payload attachment
- `GET /api/v1/vehicles/{id}/payloads` — List payload attachments
- `DELETE /api/v1/vehicles/{id}/payloads/{payload_id}` — Detach payload instance
- `GET /api/v1/vehicles/{id}/power-budget` — Query avionics + sensor + payload power budget breakdown
- `POST /api/v1/simulation/fail-sensor` — Inject real-time sensor failure into running simulation

## Physical Provenance & Verification

- Provenance metadata explicitly tags sensor mass as `HARDWARE_SPEC` and offset CoM shift as `ESTIMATED`.
- High-rate normalized sensor telemetry structures (`IMUSample`, `GPSSample`, `RangefinderSample`, `CameraMetadataSample`) ensure zero fake telemetry in live simulation channels.
