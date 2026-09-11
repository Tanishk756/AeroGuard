"""First-Order Rigid-Body Physics & Inertia Engine for UAV Configurations."""

import math
from typing import Dict, Any, List, Tuple
from app.models.hardware_registry import PersistentHardwareComponent


class RigidBodyPhysicsEngine:
    """Computes mass, center of mass, 3D inertia tensor, arm length, and motor placement."""

    @classmethod
    def compute_physical_properties(
        cls,
        frame: PersistentHardwareComponent,
        motor: PersistentHardwareComponent,
        esc: PersistentHardwareComponent,
        propeller: PersistentHardwareComponent,
        battery: PersistentHardwareComponent,
        flight_controller: PersistentHardwareComponent,
        gps: PersistentHardwareComponent = None,
        num_motors: int = 4,
        sensors: List[Any] = None,
        payloads: List[Any] = None,
    ) -> Dict[str, Any]:
        # 1. Component Masses in kg
        m_frame_kg = frame.mass_g / 1000.0
        m_motor_kg = motor.mass_g / 1000.0
        m_esc_kg = esc.mass_g / 1000.0
        m_prop_kg = propeller.mass_g / 1000.0
        m_bat_kg = battery.mass_g / 1000.0
        m_fc_kg = flight_controller.mass_g / 1000.0
        m_gps_kg = (gps.mass_g / 1000.0) if gps else 0.0

        sensors_mass_kg = sum((getattr(s, 'mass_g', 15.0) / 1000.0) for s in (sensors or []))
        payloads_mass_kg = sum((getattr(p, 'mass_g', 250.0) / 1000.0) for p in (payloads or []))

        total_mass_kg = (
            m_frame_kg
            + (m_motor_kg * num_motors)
            + (m_esc_kg * num_motors)
            + (m_prop_kg * num_motors)
            + m_bat_kg
            + m_fc_kg
            + m_gps_kg
            + sensors_mass_kg
            + payloads_mass_kg
        )

        # 2. Quad-X Geometry Setup (Wheelbase & Arm Length)
        wheelbase_mm = 450.0  # Default 450mm wheelbase
        if frame.dimensions_mm and isinstance(frame.dimensions_mm, dict):
            wheelbase_mm = float(frame.dimensions_mm.get("wheelbase_mm", 450.0))

        arm_length_m = (wheelbase_mm / 2.0) / 1000.0
        # For Quad-X (+45 deg arm offset)
        offset_m = arm_length_m * math.cos(math.radians(45))

        # Motor relative positions [(x, y, z)] in meters
        motor_positions = [
            (round(offset_m, 4), round(offset_m, 4), 0.0),    # Motor 1 (Front-Right, CCW)
            (round(-offset_m, 4), round(-offset_m, 4), 0.0),  # Motor 2 (Rear-Left, CCW)
            (round(offset_m, 4), round(-offset_m, 4), 0.0),   # Motor 3 (Front-Left, CW)
            (round(-offset_m, 4), round(offset_m, 4), 0.0),   # Motor 4 (Rear-Right, CW)
        ]

        # 3. Center of Mass Calculation (x, y, z)
        com_x = 0.0
        com_y = 0.0
        com_z = 0.0

        for s in (sensors or []):
            m_s = (getattr(s, 'mass_g', 15.0) if hasattr(s, 'mass_g') else (s.get('mass_g', 15.0) if isinstance(s, dict) else 15.0)) / 1000.0
            pos = getattr(s, 'position_json', None) or getattr(s, 'position', None) or (s.get('position') if isinstance(s, dict) else None) or {}
            if isinstance(pos, dict):
                com_x += m_s * pos.get("x", 0.0)
                com_y += m_s * pos.get("y", 0.0)
                com_z += m_s * pos.get("z", 0.0)

        for p in (payloads or []):
            m_p = (getattr(p, 'mass_g', 250.0) if hasattr(p, 'mass_g') else (p.get('mass_g', 250.0) if isinstance(p, dict) else 250.0)) / 1000.0
            pos = getattr(p, 'position_json', None) or getattr(p, 'position', None) or (p.get('position') if isinstance(p, dict) else None) or {}
            if isinstance(pos, dict):
                com_x += m_p * pos.get("x", 0.0)
                com_y += m_p * pos.get("y", 0.0)
                com_z += m_p * pos.get("z", 0.0)

        if total_mass_kg > 0:
            com = {
                "x": round(com_x / total_mass_kg, 4),
                "y": round(com_y / total_mass_kg, 4),
                "z": round(com_z / total_mass_kg, 4),
            }
        else:
            com = {"x": 0.0, "y": 0.0, "z": 0.0}

        # 4. First-Order Moment of Inertia Tensor (Ixx, Iyy, Izz) in kg*m^2
        # Central hub inertia approximation
        r_hub = 0.1  # 10cm hub radius
        i_hub = 0.5 * (m_frame_kg + m_bat_kg + m_fc_kg) * (r_hub**2)

        # Motor & rotor point-mass contributions at distance R
        r_motor = arm_length_m
        i_motors_z = num_motors * (m_motor_kg + m_prop_kg + m_esc_kg) * (r_motor**2)
        i_motors_xy = (num_motors / 2.0) * (m_motor_kg + m_prop_kg + m_esc_kg) * (r_motor**2)

        ixx = round(i_hub + i_motors_xy, 6)
        iyy = round(i_hub + i_motors_xy, 6)
        izz = round(i_hub + i_motors_z, 6)

        return {
            "total_mass_kg": round(total_mass_kg, 4),
            "total_mass_g": round(total_mass_kg * 1000.0, 1),
            "center_of_mass": com,
            "inertia": {"ixx": ixx, "iyy": iyy, "izz": izz},
            "wheelbase_mm": wheelbase_mm,
            "arm_length_m": round(arm_length_m, 4),
            "motor_positions": motor_positions,
        }
