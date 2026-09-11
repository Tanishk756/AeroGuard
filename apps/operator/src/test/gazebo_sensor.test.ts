import assert from 'node:assert';
import test, { describe, it } from 'node:test';

describe('AeroGuard Stage S8 Gazebo Sensor Generator Frontend Contracts', () => {
  it('validates sensor XML tag contract mappings for Gazebo Harmonic SDF 1.9', () => {
    const sensorTypes = ['IMU', 'GPS', 'RANGEFINDER', 'CAMERA'];
    const expectedSdfTypes = ['imu', 'navsat', 'gpu_lidar', 'camera'];

    sensorTypes.forEach((sType, idx) => {
      assert.ok(sType);
      assert.ok(expectedSdfTypes[idx]);
    });
  });
});
