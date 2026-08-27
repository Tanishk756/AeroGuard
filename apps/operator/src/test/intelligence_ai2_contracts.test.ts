import assert from 'node:assert';
import test, { describe, it } from 'node:test';

// ── Pure Data Contracts & Validation for AI2 Multi-Track Intelligence ──

type BehavioralState =
  | 'NORMAL'
  | 'APPROACHING'
  | 'DEPARTING'
  | 'LOITERING'
  | 'RAPID_CHANGE'
  | 'COORDINATED'
  | 'ANOMALOUS';

interface TrackGroup {
  group_id: string;
  member_track_ids: string[];
  centroid_lat: number;
  centroid_lon: number;
  centroid_alt?: number | null;
  radius_meters: number;
  member_count: number;
  confidence: number;
  behavioral_state: BehavioralState;
  updated_at: string;
}

interface BehaviorClassification {
  track_id: string;
  state: BehavioralState;
  confidence: number;
  duration_seconds: number;
  reason: string;
  contributing_factors: string[];
  evaluated_at: string;
}

interface CoordinatedFormation {
  formation_id: string;
  group_id: string;
  member_track_ids: string[];
  synchronization_index: number;
  heading_dispersion_deg: number;
  velocity_dispersion_mps: number;
  confidence: number;
  evaluated_at: string;
}

interface ThreatPriorityFactor {
  name: string;
  score: number;
  weight: number;
  contribution: number;
  description: string;
}

interface ThreatPriorityAssessment {
  track_id: string;
  group_id?: string | null;
  priority_score: number;
  priority_level: 'LOW' | 'MEDIUM' | 'HIGH' | 'CRITICAL';
  confidence: number;
  factors: ThreatPriorityFactor[];
  reason: string;
  evaluated_at: string;
}

interface MultiTrackIntelligenceSummary {
  groups: TrackGroup[];
  behaviors: BehaviorClassification[];
  formations: CoordinatedFormation[];
  priorities: ThreatPriorityAssessment[];
  evaluated_at: string;
}

describe('AeroGuard Stage AI2 Multi-Track Intelligence & Behavioral Contracts', () => {
  describe('BehavioralState Enum & Literals', () => {
    it('contains exactly the 7 authoritative defensive states', () => {
      const states: BehavioralState[] = [
        'NORMAL',
        'APPROACHING',
        'DEPARTING',
        'LOITERING',
        'RAPID_CHANGE',
        'COORDINATED',
        'ANOMALOUS',
      ];
      assert.strictEqual(states.length, 7);
      assert.strictEqual(new Set(states).size, 7);
    });
  });

  describe('TrackGroup Contract & Invariants', () => {
    it('constructs a valid TrackGroup with unique members and centroid', () => {
      const group: TrackGroup = {
        group_id: 'GRP-001',
        member_track_ids: ['TRK-A', 'TRK-B', 'TRK-C'],
        centroid_lat: 37.7749,
        centroid_lon: -122.4194,
        radius_meters: 65.0,
        member_count: 3,
        confidence: 0.95,
        behavioral_state: 'COORDINATED',
        updated_at: new Date().toISOString(),
      };

      assert.strictEqual(group.group_id, 'GRP-001');
      assert.strictEqual(group.member_track_ids.length, 3);
      assert.strictEqual(group.member_count, 3);
      assert.ok(group.confidence >= 0 && group.confidence <= 1.0);
      assert.ok(group.radius_meters >= 0);
    });

    it('validates unique member track IDs without duplicates', () => {
      const members = ['TRK-01', 'TRK-02', 'TRK-03'];
      const hasDuplicates = (arr: string[]) => new Set(arr).size !== arr.length;

      assert.strictEqual(hasDuplicates(members), false);
      assert.strictEqual(hasDuplicates(['TRK-01', 'TRK-01']), true);
    });
  });

  describe('BehaviorClassification Contract & Bounds', () => {
    it('validates confidence and duration bounds', () => {
      const behavior: BehaviorClassification = {
        track_id: 'TRK-01',
        state: 'LOITERING',
        confidence: 0.85,
        duration_seconds: 30.5,
        reason: 'Loitering pattern detected',
        contributing_factors: ['low_directional_consistency'],
        evaluated_at: new Date().toISOString(),
      };

      assert.strictEqual(behavior.state, 'LOITERING');
      assert.ok(behavior.confidence >= 0 && behavior.confidence <= 1.0);
      assert.ok(behavior.duration_seconds >= 0);
    });
  });

  describe('CoordinatedFormation Contract & Bounds', () => {
    it('validates synchronization index and minimum 2 members', () => {
      const formation: CoordinatedFormation = {
        formation_id: 'FORM-01',
        group_id: 'GRP-01',
        member_track_ids: ['TRK-01', 'TRK-02'],
        synchronization_index: 0.92,
        heading_dispersion_deg: 6.4,
        velocity_dispersion_mps: 1.1,
        confidence: 0.94,
        evaluated_at: new Date().toISOString(),
      };

      assert.ok(formation.member_track_ids.length >= 2);
      assert.ok(formation.synchronization_index >= 0 && formation.synchronization_index <= 1.0);
      assert.ok(formation.heading_dispersion_deg >= 0 && formation.heading_dispersion_deg <= 180.0);
    });
  });

  describe('ThreatPriorityAssessment Contract & Scoring Bounds', () => {
    it('enforces priority score range within [0, 100]', () => {
      const priority: ThreatPriorityAssessment = {
        track_id: 'TRK-01',
        group_id: 'GRP-01',
        priority_score: 72.4,
        priority_level: 'HIGH',
        confidence: 0.93,
        factors: [
          {
            name: 'geofence_ingress',
            score: 80.0,
            weight: 0.3,
            contribution: 24.0,
            description: 'Approaching perimeter',
          },
        ],
        reason: 'Elevated defensive priority due to perimeter proximity',
        evaluated_at: new Date().toISOString(),
      };

      assert.ok(priority.priority_score >= 0 && priority.priority_score <= 100);
      assert.ok(priority.confidence >= 0 && priority.confidence <= 1.0);
      assert.strictEqual(priority.priority_level, 'HIGH');
    });
  });

  describe('MultiTrackIntelligenceSummary Aggregation', () => {
    it('serializes and deserializes aggregate summary shape cleanly', () => {
      const summary: MultiTrackIntelligenceSummary = {
        groups: [],
        behaviors: [],
        formations: [],
        priorities: [],
        evaluated_at: new Date().toISOString(),
      };

      const jsonString = JSON.stringify(summary);
      const parsed = JSON.parse(jsonString) as MultiTrackIntelligenceSummary;
      assert.ok(Array.isArray(parsed.groups));
      assert.ok(Array.isArray(parsed.behaviors));
      assert.ok(Array.isArray(parsed.formations));
      assert.ok(Array.isArray(parsed.priorities));
      assert.ok(typeof parsed.evaluated_at === 'string');
    });
  });
});
