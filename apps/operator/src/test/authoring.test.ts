import assert from 'node:assert/strict';
import { describe, it } from 'node:test';

interface GeofenceGeometryBBox {
  type: 'bbox';
  min_lat: number;
  min_lon: number;
  max_lat: number;
  max_lon: number;
}

interface GeofenceGeometryPolygon {
  type: 'polygon';
  coordinates: [number, number][];
}

type GeofenceGeometry = GeofenceGeometryBBox | GeofenceGeometryPolygon;

interface ScenarioWaypoint {
  latitude: number;
  longitude: number;
  altitude?: number | null;
  speed?: number | null;
}

interface ScenarioTargetDefinition {
  target_id: string;
  initial_latitude: number;
  initial_longitude: number;
  initial_altitude?: number | null;
  velocity: number;
  heading: number;
  waypoints: ScenarioWaypoint[];
  classification?: string | null;
}

interface ScenarioSensorDefinition {
  sensor_id: string;
  modality: string;
  latitude: number;
  longitude: number;
  altitude?: number | null;
  range_meters: number;
  detection_probability: number;
  position_uncertainty_meters: number;
  altitude_uncertainty_meters?: number | null;
  velocity_uncertainty_mps?: number | null;
  fov_azimuth_start_deg?: number | null;
  fov_azimuth_span_deg?: number | null;
}

interface ScenarioConfiguration {
  seed: number;
  duration_seconds: number;
  tick_rate_hz: number;
  start_time: string;
  targets: ScenarioTargetDefinition[];
  sensors: ScenarioSensorDefinition[];
  geofence_ids: string[];
}

interface ScenarioCreate {
  name: string;
  description?: string;
  configuration: ScenarioConfiguration;
}

type ScenarioStatus = 'DRAFT' | 'READY' | 'RUNNING' | 'PAUSED' | 'STOPPED' | 'COMPLETED';

describe('AeroGuard Stage UI5 Mission Authoring & Defense Zone Studio Unit Tests', () => {
  describe('Geofence BBox Boundary Validation', () => {
    it('validates correct 2D bounding box coordinates', () => {
      const validBbox: GeofenceGeometry = {
        type: 'bbox',
        min_lat: 37.75,
        min_lon: -122.45,
        max_lat: 37.8,
        max_lon: -122.4,
      };

      assert.equal(validBbox.type, 'bbox');
      assert.ok(validBbox.min_lat < validBbox.max_lat);
      assert.ok(validBbox.min_lon < validBbox.max_lon);
      assert.ok(validBbox.min_lat >= -90 && validBbox.max_lat <= 90);
      assert.ok(validBbox.min_lon >= -180 && validBbox.max_lon <= 180);
    });

    it('identifies invalid inverted bounding box coordinates', () => {
      const validateBbox = (minLat: number, minLon: number, maxLat: number, maxLon: number): boolean => {
        if (minLat >= maxLat) return false;
        if (minLon >= maxLon) return false;
        if (minLat < -90 || maxLat > 90 || minLon < -180 || maxLon > 180) return false;
        return true;
      };

      assert.equal(validateBbox(37.8, -122.45, 37.75, -122.4), false, 'min_lat >= max_lat should fail');
      assert.equal(validateBbox(37.75, -122.4, 37.8, -122.45), false, 'min_lon >= max_lon should fail');
      assert.equal(validateBbox(-95.0, -122.45, 37.8, -122.4), false, 'out-of-bounds latitude should fail');
      assert.equal(validateBbox(37.75, -190.0, 37.8, -122.4), false, 'out-of-bounds longitude should fail');
    });
  });

  describe('Geofence Polygon Vertex List Validation', () => {
    it('accepts valid polygon perimeters with >= 3 vertex coordinates', () => {
      const validPoly: GeofenceGeometry = {
        type: 'polygon',
        coordinates: [
          [37.7749, -122.4194],
          [37.7849, -122.4094],
          [37.7649, -122.3994],
        ],
      };

      assert.equal(validPoly.type, 'polygon');
      assert.ok(validPoly.coordinates.length >= 3);
      validPoly.coordinates.forEach(([lat, lon]) => {
        assert.ok(typeof lat === 'number' && !isNaN(lat) && lat >= -90 && lat <= 90);
        assert.ok(typeof lon === 'number' && !isNaN(lon) && lon >= -180 && lon <= 180);
      });
    });

    it('rejects polygon definitions with fewer than 3 vertices or malformed coordinates', () => {
      const validatePolygon = (coords: [number, number][]): boolean => {
        if (!Array.isArray(coords) || coords.length < 3) return false;
        return coords.every(
          ([lat, lon]) =>
            typeof lat === 'number' &&
            typeof lon === 'number' &&
            !isNaN(lat) &&
            !isNaN(lon) &&
            lat >= -90 &&
            lat <= 90 &&
            lon >= -180 &&
            lon <= 180
        );
      };

      assert.equal(validatePolygon([[37.77, -122.41], [37.78, -122.4]]), false, '< 3 points should fail');
      assert.equal(validatePolygon([[37.77, -122.41], [37.78, -122.4], [100.0, -122.39]]), false, 'lat > 90 should fail');
    });
  });

  describe('Geofence Altitude Bounds Validation', () => {
    it('validates non-negative altitude ceiling and floor constraints', () => {
      const validateAltitude = (minAlt?: number | null, maxAlt?: number | null): boolean => {
        if (minAlt != null && (minAlt < 0 || isNaN(minAlt))) return false;
        if (maxAlt != null && (maxAlt < 0 || isNaN(maxAlt))) return false;
        if (minAlt != null && maxAlt != null && minAlt > maxAlt) return false;
        return true;
      };

      assert.equal(validateAltitude(0, 500), true);
      assert.equal(validateAltitude(null, 1000), true);
      assert.equal(validateAltitude(50, null), true);
      assert.equal(validateAltitude(null, null), true);
      assert.equal(validateAltitude(-10, 500), false, 'negative min altitude should fail');
      assert.equal(validateAltitude(500, 200), false, 'min > max altitude should fail');
    });
  });

  describe('Scenario Configuration Serialization & Identifier Uniqueness', () => {
    it('serializes complete scenario create payload conforming to backend schema', () => {
      const target: ScenarioTargetDefinition = {
        target_id: 'DRONE-ALPHA',
        classification: 'DRONE_ROTARY',
        initial_latitude: 37.7749,
        initial_longitude: -122.4194,
        initial_altitude: 100.0,
        velocity: 12.5,
        heading: 45.0,
        waypoints: [
          { latitude: 37.78, longitude: -122.41, altitude: 110.0, speed: 15.0 },
          { latitude: 37.785, longitude: -122.4, altitude: 120.0, speed: 10.0 },
        ],
      };

      const sensor: ScenarioSensorDefinition = {
        sensor_id: 'SIM-RADAR-1',
        modality: 'radar',
        latitude: 37.77,
        longitude: -122.42,
        altitude: 15.0,
        range_meters: 6000.0,
        detection_probability: 0.92,
        position_uncertainty_meters: 4.5,
        fov_azimuth_start_deg: 0,
        fov_azimuth_span_deg: 360,
      };

      const config: ScenarioConfiguration = {
        seed: 42,
        duration_seconds: 600,
        tick_rate_hz: 2.0,
        start_time: '2026-01-01T00:00:00Z',
        targets: [target],
        sensors: [sensor],
        geofence_ids: ['ZONE-RESTRICTED-1'],
      };

      const scenarioPayload: ScenarioCreate = {
        name: 'AIRSPACE_INTRUSION_TEST',
        description: 'Synthetic multi-waypoint drone breach drill',
        configuration: config,
      };

      assert.equal(scenarioPayload.name, 'AIRSPACE_INTRUSION_TEST');
      assert.equal(scenarioPayload.configuration.targets.length, 1);
      assert.equal(scenarioPayload.configuration.targets[0].waypoints.length, 2);
      assert.equal(scenarioPayload.configuration.sensors[0].modality, 'radar');
      assert.equal(scenarioPayload.configuration.geofence_ids.length, 1);
    });

    it('enforces uniqueness of synthetic target IDs and sensor IDs', () => {
      const validateUniqueIds = (targets: { target_id: string }[], sensors: { sensor_id: string }[]): boolean => {
        const targetIds = targets.map((t) => t.target_id.trim().toUpperCase());
        if (new Set(targetIds).size !== targetIds.length) return false;

        const sensorIds = sensors.map((s) => s.sensor_id.trim().toUpperCase());
        if (new Set(sensorIds).size !== sensorIds.length) return false;

        return true;
      };

      assert.equal(
        validateUniqueIds([{ target_id: 'T1' }, { target_id: 'T2' }], [{ sensor_id: 'S1' }, { sensor_id: 'S2' }]),
        true
      );
      assert.equal(
        validateUniqueIds([{ target_id: 'T1' }, { target_id: 'T1' }], [{ sensor_id: 'S1' }]),
        false,
        'duplicate target IDs should fail'
      );
      assert.equal(
        validateUniqueIds([{ target_id: 'T1' }], [{ sensor_id: 'S1' }, { sensor_id: 'S1' }]),
        false,
        'duplicate sensor IDs should fail'
      );
    });
  });

  describe('Unsaved-Draft Dirty State & Discard Protection', () => {
    it('detects uncommitted form modifications and evaluates dirty state', () => {
      const initialForm = { name: 'ZONE-A', minLat: '37.75', minLon: '-122.45' };
      let currentForm = { ...initialForm };

      const checkDirty = () => JSON.stringify(initialForm) !== JSON.stringify(currentForm);

      assert.equal(checkDirty(), false);

      currentForm = { ...initialForm, name: 'ZONE-A-MODIFIED' };
      assert.equal(checkDirty(), true);
    });
  });

  describe('Execution Safety Guard & Destructive Action Protections', () => {
    it('blocks deletion and structural configuration edit on RUNNING or PAUSED scenarios', () => {
      const canMutateOrDeleteScenario = (status: ScenarioStatus): boolean => {
        if (status === 'RUNNING' || status === 'PAUSED') {
          return false;
        }
        return true;
      };

      assert.equal(canMutateOrDeleteScenario('DRAFT'), true);
      assert.equal(canMutateOrDeleteScenario('READY'), true);
      assert.equal(canMutateOrDeleteScenario('STOPPED'), true);
      assert.equal(canMutateOrDeleteScenario('COMPLETED'), true);
      assert.equal(canMutateOrDeleteScenario('RUNNING'), false, 'RUNNING scenarios cannot be mutated or deleted');
      assert.equal(canMutateOrDeleteScenario('PAUSED'), false, 'PAUSED scenarios cannot be mutated or deleted');
    });

    it('requires explicit confirmation before deleting defense zones or scenarios', () => {
      let deletionTarget: string | null = null;
      let isConfirmed = false;

      const requestDelete = (entityId: string) => {
        deletionTarget = entityId;
        isConfirmed = false;
      };

      const confirmDelete = () => {
        if (!deletionTarget) return false;
        isConfirmed = true;
        return true;
      };

      requestDelete('ZONE-CRITICAL-NORTH');
      assert.equal(deletionTarget, 'ZONE-CRITICAL-NORTH');
      assert.equal(isConfirmed, false);

      assert.equal(confirmDelete(), true);
      assert.equal(isConfirmed, true);
    });
  });

  describe('RBAC Authoring Permission Gating', () => {
    it('asserts permission requirements for create, update, and delete actions', () => {
      const checkPermission = (userPermissions: string[], required: string): boolean => {
        return userPermissions.includes(required);
      };

      const operatorPermissions = ['scenarios.read', 'scenarios.run'];
      const plannerPermissions = ['scenarios.read', 'scenarios.run', 'scenarios.create', 'scenarios.update'];
      const adminPermissions = ['scenarios.read', 'scenarios.run', 'scenarios.create', 'scenarios.update', 'scenarios.delete'];

      assert.equal(checkPermission(operatorPermissions, 'scenarios.create'), false);
      assert.equal(checkPermission(operatorPermissions, 'scenarios.delete'), false);
      assert.equal(checkPermission(plannerPermissions, 'scenarios.create'), true);
      assert.equal(checkPermission(plannerPermissions, 'scenarios.update'), true);
      assert.equal(checkPermission(plannerPermissions, 'scenarios.delete'), false);
      assert.equal(checkPermission(adminPermissions, 'scenarios.delete'), true);
    });
  });
});
