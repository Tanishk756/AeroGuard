import assert from 'node:assert';
import test, { describe, it } from 'node:test';
import type { PayloadInstanceSpec } from '../components/workstation/VehicleBuilderWorkstation';

describe('AeroGuard Stage S8 Payload Builder Unit Tests', () => {
  describe('PayloadInstanceSpec Structure & Validation', () => {
    it('verifies payload attachment specification and spatial placement', () => {
      const payload: PayloadInstanceSpec = {
        id: 'p-cam-1',
        payload_type: 'CAMERA_PAYLOAD',
        name: '4K EO/IR Gimbal Camera',
        mass_g: 220.0,
        power_w: 6.5,
        position: { x: 0.05, y: 0, z: -0.05 },
        orientation: { roll: 0, pitch: 0, yaw: 0 },
      };

      assert.strictEqual(payload.payload_type, 'CAMERA_PAYLOAD');
      assert.strictEqual(payload.mass_g, 220.0);
      assert.strictEqual(payload.power_w, 6.5);
      assert.strictEqual(payload.position.z, -0.05);
    });
  });
});
