import assert from 'node:assert';
import test, { describe, it } from 'node:test';
import type { SensorInstanceSpec } from '../components/workstation/VehicleBuilderWorkstation';

describe('AeroGuard Stage S8 Sensor Builder Unit Tests', () => {
  describe('SensorInstanceSpec Structure & Validation', () => {
    it('verifies sensor instance specification with update rates and health state', () => {
      const sensor: SensorInstanceSpec = {
        id: 's-imu-1',
        sensor_type: 'IMU',
        name: 'Primary Nav IMU',
        mass_g: 15.0,
        power_w: 0.5,
        position: { x: 0, y: 0, z: 0.05 },
        orientation: { roll: 0, pitch: 0, yaw: 0 },
        update_rate_hz: 250,
        health_status: 'OK',
      };

      assert.strictEqual(sensor.sensor_type, 'IMU');
      assert.strictEqual(sensor.mass_g, 15.0);
      assert.strictEqual(sensor.update_rate_hz, 250);
      assert.strictEqual(sensor.health_status, 'OK');
    });
  });
});
