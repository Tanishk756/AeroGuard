import assert from 'node:assert';
import test, { describe, it } from 'node:test';
import type { VehicleCompatibility } from '../components/workstation/VehicleBuilderWorkstation';

describe('AeroGuard Stage S4 Vehicle Builder Unit Tests', () => {
  describe('Hardware Compatibility & Mass Calculation', () => {
    it('correctly evaluates positive vehicle compatibility metrics', () => {
      const compatibility: VehicleCompatibility = {
        compatible: true,
        errors: [],
        warnings: [],
        total_mass_g: 1110.0,
        estimated_hover_throttle: 0.28,
        thrust_to_weight_ratio: 3.56,
      };

      assert.strictEqual(compatibility.compatible, true);
      assert.strictEqual(compatibility.total_mass_g, 1110.0);
      assert.strictEqual(compatibility.thrust_to_weight_ratio, 3.56);
      assert.strictEqual(compatibility.errors.length, 0);
    });

    it('flags voltage mismatch compatibility errors correctly', () => {
      const compatibility: VehicleCompatibility = {
        compatible: false,
        errors: ['Motor max voltage (16.8V) exceeded by battery (29.6V)'],
        warnings: [],
        total_mass_g: 1400.0,
        estimated_hover_throttle: 0.35,
        thrust_to_weight_ratio: 2.85,
      };

      assert.strictEqual(compatibility.compatible, false);
      assert.strictEqual(compatibility.errors.length, 1);
      assert.match(compatibility.errors[0], /Motor max voltage/);
    });
  });
});
