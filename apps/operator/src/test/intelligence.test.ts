import assert from 'node:assert';
import test, { describe, it } from 'node:test';

type AnomalyCategory =
  | 'NORMAL'
  | 'UNUSUAL_KINEMATICS'
  | 'RAPID_ALTITUDE_CHANGE'
  | 'ERRATIC_HEADING'
  | 'EXCESSIVE_ACCELERATION'
  | 'LOITERING_PATTERN'
  | 'TRAJECTORY_DEVIATION';

type AnomalySeverity = 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';

interface KinematicFeatures {
  speed_mps: number;
  acceleration_mps2: number;
  vertical_speed_mps: number;
  heading_deg?: number | null;
  turn_rate_dps: number;
  speed_variance: number;
  altitude_variance: number;
  acceleration_variance: number;
  trajectory_curvature: number;
  loiter_radius_meters?: number | null;
  directional_consistency: number;
  sample_count: number;
  timespan_seconds: number;
}

interface AnomalyAssessment {
  track_id: string;
  anomaly_score: number;
  anomaly_level: AnomalySeverity;
  primary_category: AnomalyCategory;
  sensor_confidence: number;
  factors: Array<{
    name: string;
    score: number;
    weight: number;
    contribution: number;
    severity: AnomalySeverity;
    description: string;
  }>;
  summary: string;
  evaluated_at: string;
}

interface TrajectoryWayPoint {
  timestamp: string;
  time_offset_seconds: number;
  latitude: number;
  longitude: number;
  altitude?: number | null;
  uncertainty_radius_meters: number;
}

interface TrajectoryPrediction {
  track_id: string;
  prediction_horizon_seconds: number;
  model_type: string;
  waypoints: TrajectoryWayPoint[];
  generated_at: string;
}

interface GeofenceIngressEstimate {
  track_id: string;
  geofence_id: string;
  geofence_name: string;
  estimated_time_to_breach_seconds?: number | null;
  intersection_latitude?: number | null;
  intersection_longitude?: number | null;
  status: 'INSIDE' | 'APPROACHING' | 'DIVERGING' | 'NO_INTERSECTION';
  evaluated_at: string;
}

interface DefensiveIntelligenceSummary {
  track_id: string;
  features: KinematicFeatures;
  anomaly: AnomalyAssessment;
  trajectory: TrajectoryPrediction;
  ingress_estimates: GeofenceIngressEstimate[];
  evaluated_at: string;
}

describe('AeroGuard Stage AI1 Defensive Intelligence Frontend Unit Tests', () => {
  describe('Anomaly Severity & Status Mapping', () => {
    const getAnomalyColor = (score: number): string => {
      if (score >= 80) return 'var(--status-critical)';
      if (score >= 60) return '#fb923c';
      if (score >= 30) return 'var(--status-warning)';
      return 'var(--status-success)';
    };

    const getAnomalyLevel = (score: number): 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL' => {
      if (score >= 80) return 'CRITICAL';
      if (score >= 60) return 'HIGH';
      if (score >= 30) return 'MEDIUM';
      return 'LOW';
    };

    it('classifies nominal flight as LOW severity', () => {
      const score = 12.5;
      assert.strictEqual(getAnomalyLevel(score), 'LOW');
      assert.strictEqual(getAnomalyColor(score), 'var(--status-success)');
    });

    it('classifies moderate deviations as MEDIUM severity', () => {
      const score = 42.0;
      assert.strictEqual(getAnomalyLevel(score), 'MEDIUM');
      assert.strictEqual(getAnomalyColor(score), 'var(--status-warning)');
    });

    it('classifies high turn rate / climb anomalies as HIGH severity', () => {
      const score = 68.4;
      assert.strictEqual(getAnomalyLevel(score), 'HIGH');
      assert.strictEqual(getAnomalyColor(score), '#fb923c');
    });

    it('classifies critical loiter / erratic dive as CRITICAL severity', () => {
      const score = 88.9;
      assert.strictEqual(getAnomalyLevel(score), 'CRITICAL');
      assert.strictEqual(getAnomalyColor(score), 'var(--status-critical)');
    });
  });

  describe('Kinematic Feature Formatting & Explainability', () => {
    const sampleFeatures: KinematicFeatures = {
      speed_mps: 22.4,
      acceleration_mps2: 3.8,
      vertical_speed_mps: -8.5,
      heading_deg: 185.2,
      turn_rate_dps: 42.1,
      speed_variance: 4.2,
      altitude_variance: 16.8,
      acceleration_variance: 1.1,
      trajectory_curvature: 0.08,
      loiter_radius_meters: 65.4,
      directional_consistency: 0.15,
      sample_count: 12,
      timespan_seconds: 45.0,
    };

    it('formats turn rate with degree per second units', () => {
      const turnStr = `${sampleFeatures.turn_rate_dps.toFixed(1)}°/s`;
      assert.strictEqual(turnStr, '42.1°/s');
    });

    it('formats climb/descent rate with m/s units', () => {
      const vertStr = `${sampleFeatures.vertical_speed_mps.toFixed(1)} m/s`;
      assert.strictEqual(vertStr, '-8.5 m/s');
    });

    it('formats loiter radius with approximate meters', () => {
      assert.ok(sampleFeatures.loiter_radius_meters !== null);
      const loiterStr = `~${sampleFeatures.loiter_radius_meters?.toFixed(0)}m`;
      assert.strictEqual(loiterStr, '~65m');
    });

    it('formats directional consistency as percentage', () => {
      const consStr = `${(sampleFeatures.directional_consistency * 100).toFixed(0)}%`;
      assert.strictEqual(consStr, '15%');
    });
  });

  describe('Geofence Ingress Forecast & Time-to-Breach', () => {
    const sampleIngress: GeofenceIngressEstimate[] = [
      {
        track_id: 'TRK-001',
        geofence_id: 'GEO-01',
        geofence_name: 'Alpha Perimeter',
        estimated_time_to_breach_seconds: 24.6,
        intersection_latitude: 37.7812,
        intersection_longitude: -122.4150,
        status: 'APPROACHING',
        evaluated_at: '2026-08-27T03:00:00Z',
      },
      {
        track_id: 'TRK-001',
        geofence_id: 'GEO-02',
        geofence_name: 'Bravo Core',
        estimated_time_to_breach_seconds: null,
        status: 'DIVERGING',
        evaluated_at: '2026-08-27T03:00:00Z',
      },
    ];

    it('identifies imminent geofence breach risks', () => {
      const activeRisks = sampleIngress.filter(
        (e) => e.status === 'APPROACHING' || e.status === 'INSIDE'
      );
      assert.strictEqual(activeRisks.length, 1);
      assert.strictEqual(activeRisks[0].geofence_name, 'Alpha Perimeter');
    });

    it('formats time-to-breach correctly', () => {
      const risk = sampleIngress[0];
      const breachStr = `Ingress in ~${risk.estimated_time_to_breach_seconds?.toFixed(0)}s`;
      assert.strictEqual(breachStr, 'Ingress in ~25s');
    });
  });

  describe('Trajectory Prediction & Waypoint Projection', () => {
    const sampleTrajectory: TrajectoryPrediction = {
      track_id: 'TRK-001',
      prediction_horizon_seconds: 60.0,
      model_type: 'CONSTANT_VELOCITY_TURN',
      waypoints: [
        {
          timestamp: '2026-08-27T03:00:05Z',
          time_offset_seconds: 5.0,
          latitude: 37.7755,
          longitude: -122.4188,
          altitude: 120.0,
          uncertainty_radius_meters: 20.0,
        },
        {
          timestamp: '2026-08-27T03:00:30Z',
          time_offset_seconds: 30.0,
          latitude: 37.7785,
          longitude: -122.4150,
          altitude: 120.0,
          uncertainty_radius_meters: 70.0,
        },
        {
          timestamp: '2026-08-27T03:01:00Z',
          time_offset_seconds: 60.0,
          latitude: 37.7820,
          longitude: -122.4100,
          altitude: 120.0,
          uncertainty_radius_meters: 130.0,
        },
      ],
      generated_at: '2026-08-27T03:00:00Z',
    };

    it('has predicted waypoints reaching horizon', () => {
      assert.strictEqual(sampleTrajectory.prediction_horizon_seconds, 60.0);
      assert.strictEqual(sampleTrajectory.waypoints.length, 3);
      assert.strictEqual(sampleTrajectory.waypoints[2].time_offset_seconds, 60.0);
    });

    it('exhibits expanding uncertainty envelopes over time', () => {
      const u0 = sampleTrajectory.waypoints[0].uncertainty_radius_meters;
      const u1 = sampleTrajectory.waypoints[1].uncertainty_radius_meters;
      const u2 = sampleTrajectory.waypoints[2].uncertainty_radius_meters;

      assert.ok(u0 < u1, 'Uncertainty at 30s must exceed uncertainty at 5s');
      assert.ok(u1 < u2, 'Uncertainty at 60s must exceed uncertainty at 30s');
    });
  });

  describe('Realtime Intelligence Store Reducer', () => {
    interface State {
      intelligence: Record<string, DefensiveIntelligenceSummary>;
    }

    const reduceIntelligence = (
      state: State,
      summary: DefensiveIntelligenceSummary
    ): State => {
      return {
        ...state,
        intelligence: {
          ...state.intelligence,
          [summary.track_id]: summary,
        },
      };
    };

    it('adds new track intelligence summary to store', () => {
      const initial: State = { intelligence: {} };
      const summary: DefensiveIntelligenceSummary = {
        track_id: 'TRK-999',
        features: {
          speed_mps: 15.0,
          acceleration_mps2: 0.5,
          vertical_speed_mps: 0.0,
          heading_deg: 90.0,
          turn_rate_dps: 1.0,
          speed_variance: 0.2,
          altitude_variance: 0.5,
          acceleration_variance: 0.1,
          trajectory_curvature: 0.01,
          directional_consistency: 0.95,
          sample_count: 8,
          timespan_seconds: 30.0,
        },
        anomaly: {
          track_id: 'TRK-999',
          anomaly_score: 15.0,
          anomaly_level: 'LOW',
          primary_category: 'NORMAL',
          sensor_confidence: 0.92,
          factors: [],
          summary: 'Nominal trajectory parameters.',
          evaluated_at: '2026-08-27T03:00:00Z',
        },
        trajectory: {
          track_id: 'TRK-999',
          prediction_horizon_seconds: 60.0,
          model_type: 'CONSTANT_VELOCITY',
          waypoints: [],
          generated_at: '2026-08-27T03:00:00Z',
        },
        ingress_estimates: [],
        evaluated_at: '2026-08-27T03:00:00Z',
      };

      const updated = reduceIntelligence(initial, summary);
      assert.ok(updated.intelligence['TRK-999']);
      assert.strictEqual(updated.intelligence['TRK-999'].anomaly.anomaly_score, 15.0);
      assert.strictEqual(updated.intelligence['TRK-999'].anomaly.anomaly_level, 'LOW');
    });
  });
});
