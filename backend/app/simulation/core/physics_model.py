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
    ) -> Dict[str, Any]:
        # 1. Component Masses in kg
        m_frame_kg = frame.mass_g / 1000.0
        m_motor_kg = motor.mass_g / 1000.0
        m_esc_kg = esc.mass_g / 1000.0
        m_prop_kg = propeller.mass_g / 1000.0
        m_bat_kg = battery.mass_g / 1000.0
        m_fc_kg = flight_controller.mass_g / 1000.0
        m_gps_kg = (gps.mass_g / 1000.0) if gps else 0.0

        total_mass_kg = (
            m_frame_kg
            + (m_motor_kg * num_motors)
            + (m_esc_kg * num_motors)
            + (m_prop_kg * num_motors)
            + m_bat_kg
            + m_fc_kg
            + m_gps_kg
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
        # Symmetry assumes CoM near origin (0, 0, 0)
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
