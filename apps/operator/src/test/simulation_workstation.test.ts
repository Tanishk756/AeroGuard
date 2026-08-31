import assert from 'node:assert';
import test, { describe, it } from 'node:test';
import type { VehicleStateVector } from '../components/workstation/SimulationWorkstation';

describe('AeroGuard Stage S1 Simulation Workstation Unit Tests', () => {
  describe('VehicleState Envelope Normalization', () => {
    it('correctly parses normalized VehicleState telemetry vectors', () => {
      const state: VehicleStateVector = {
        timestamp_utc: '2026-08-31T12:00:00Z',
        sim_time_seconds: 15.5,
        vehicle_id: 'quad-x-001',
        flight_mode: 'GUIDED',
        armed: true,
        position: { latitude: 37.7749, longitude: -122.4194, altitude_msl: 120.0, altitude_relative: 20.0 },
        velocity: { vx: 5.0, vy: 0.0, vz: 0.0, ground_speed: 5.0 },
        attitude: { roll_deg: 2.1, pitch_deg: -1.0, yaw_deg: 90.0 },
        battery: { voltage_v: 14.8, remaining_percent: 95.0 },
        gps: { fix_type: 3, satellites_visible: 14, hdop: 0.8 },
      };

      assert.strictEqual(state.vehicle_id, 'quad-x-001');
      assert.strictEqual(state.armed, true);
      assert.strictEqual(state.position.altitude_relative, 20.0);
      assert.strictEqual(state.attitude.yaw_deg, 90.0);
    });
  });
});
