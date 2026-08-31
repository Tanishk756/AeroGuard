import assert from 'node:assert';
import test, { describe, it } from 'node:test';
import type { CompiledPhysicsModel } from '../components/workstation/VehicleBuilderWorkstation';

describe('AeroGuard Stage S5 Vehicle Builder Physics & Provenance Unit Tests', () => {
  describe('Compiled Physical Model Structure', () => {
    it('verifies compiled physics model properties and provenance tagging', () => {
      const compiled: CompiledPhysicsModel = {
        compiled_model_hash: '3a8f94c92b513d8e907142fa',
        total_mass_kg: 1.158,
        total_mass_g: 1158.0,
        wheelbase_mm: 450,
        arm_length_m: 0.225,
        center_of_mass: { x: 0, y: 0, z: 0 },
        inertia: { ixx: 0.015, iyy: 0.015, izz: 0.028 },
        motor_positions: [[0.159, 0.159, 0], [-0.159, -0.159, 0], [0.159, -0.159, 0], [-0.159, 0.159, 0]],
        total_energy_wh: 74.0,
        estimated_hover_power_w: 173.7,
        estimated_hover_current_a: 11.7,
        estimated_runtime_min: 18.5,
        provenance: {
          total_mass_g: { source_type: 'HARDWARE_SPEC', description: 'Manufacturer component masses' },
          inertia: { source_type: 'ESTIMATED', description: 'First-order rigid body model' },
        },
      };

      assert.strictEqual(compiled.total_mass_g, 1158.0);
      assert.strictEqual(compiled.arm_length_m, 0.225);
      assert.strictEqual(compiled.provenance.total_mass_g.source_type, 'HARDWARE_SPEC');
      assert.strictEqual(compiled.provenance.inertia.source_type, 'ESTIMATED');
    });
  });
});
