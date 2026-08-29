import React from 'react';
import {
  CoordinatedFormation,
  Incident,
  TrackGroup,
} from '../../types';
import { BehaviorBadge } from './BehaviorBadge';

interface GroupIntelligencePanelProps {
  group: TrackGroup;
  formation?: CoordinatedFormation | null;
  relatedIncidents?: Incident[];
  selectedTrackId?: string | null;
  onSelectTrack?: (trackId: string) => void;
  onSelectIncident?: (incidentId: string) => void;
}

export const GroupIntelligencePanel: React.FC<GroupIntelligencePanelProps> = ({
  group,
  formation,
  relatedIncidents = [],
  selectedTrackId,
  onSelectTrack,
  onSelectIncident,
}) => {
  return (
    <div
      role="region"
      aria-label={`Defensive Group Intelligence for ${group.group_id}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-md, 12px)',
        padding: 'var(--space-md, 12px)',
        backgroundColor: 'var(--bg-surface, #1e293b)',
        border: '1px solid var(--border-subtle, #334155)',
        borderRadius: 'var(--radius-md, 6px)',
      }}
    >
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderBottom: '1px solid var(--border-subtle, #334155)', paddingBottom: '8px' }}>
        <div>
          <span className="uppercase-tracking text-muted" style={{ fontSize: '9px', fontWeight: 600 }}>
            Track Group Analysis
          </span>
          <h4 className="font-mono text-sm" style={{ margin: 0, fontWeight: 700, color: '#c084fc' }}>
            {group.group_id}
          </h4>
        </div>
        <BehaviorBadge state={group.behavioral_state} confidence={group.confidence} />
      </div>

      {/* Spatial Geometry & Extent */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px', fontSize: '11px' }}>
        <div>
          <span className="text-muted" style={{ fontSize: '9.5px' }}>Centroid</span>
          <div className="font-mono" style={{ color: 'var(--text-primary, #f8fafc)' }}>
            {group.centroid_lat.toFixed(4)}°, {group.centroid_lon.toFixed(4)}°
          </div>
        </div>
        <div>
          <span className="text-muted" style={{ fontSize: '9.5px' }}>Spatial Radius</span>
          <div className="font-mono" style={{ color: 'var(--text-primary, #f8fafc)' }}>
            ~{group.radius_meters.toFixed(0)} meters
          </div>
        </div>
      </div>

      {/* Formation Coordination (if coordinated) */}
      {formation && (
        <div
          style={{
            padding: '8px',
            backgroundColor: 'rgba(168, 85, 247, 0.08)',
            border: '1px solid rgba(168, 85, 247, 0.3)',
            borderRadius: 'var(--radius-sm, 4px)',
            fontSize: '11px',
          }}
        >
          <div className="uppercase-tracking" style={{ fontSize: '9px', color: '#c084fc', fontWeight: 700, marginBottom: '4px' }}>
            ⬡ Swarm / Formation Coordination
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '4px' }}>
            <div>
              <span className="text-muted" style={{ fontSize: '9px' }}>Sync Index</span>
              <div className="font-mono" style={{ fontWeight: 700, color: '#c084fc' }}>
                {(formation.synchronization_index * 100).toFixed(0)}%
              </div>
            </div>
            <div>
              <span className="text-muted" style={{ fontSize: '9px' }}>Heading Disp.</span>
              <div className="font-mono" style={{ fontWeight: 600 }}>
                {formation.heading_dispersion_deg.toFixed(1)}°
              </div>
            </div>
            <div>
              <span className="text-muted" style={{ fontSize: '9px' }}>Vel Disp.</span>
              <div className="font-mono" style={{ fontWeight: 600 }}>
                {formation.velocity_dispersion_mps.toFixed(1)} m/s
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Associated Incidents (IM1-F) */}
      {relatedIncidents.length > 0 && (
        <div>
          <div className="uppercase-tracking text-muted" style={{ fontSize: '9px', fontWeight: 700, marginBottom: '6px' }}>
            Associated Incidents ({relatedIncidents.length})
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {relatedIncidents.map((inc) => (
              <div
                key={inc.id}
                style={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  padding: '6px 8px',
                  backgroundColor: 'rgba(0, 0, 0, 0.2)',
                  borderRadius: '4px',
                  borderLeft: `3px solid ${inc.severity === 'CRITICAL' ? '#ef4444' : inc.severity === 'HIGH' ? '#f59e0b' : '#3b82f6'}`,
                  fontSize: '11px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                  <span className="font-mono font-bold" style={{ color: 'var(--text-primary, #f8fafc)' }}>
                    {inc.incident_number}
                  </span>
                  <span className="font-mono text-muted">[{inc.status}]</span>
                </div>
                {onSelectIncident && (
                  <button
                    type="button"
                    onClick={() => onSelectIncident(inc.id)}
                    className="btn btn-secondary btn-xs font-mono"
                    style={{ padding: '2px 6px', fontSize: '10px' }}
                  >
                    Open Incident
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Member Tracks List */}
      <div>
        <div className="uppercase-tracking text-muted" style={{ fontSize: '9px', fontWeight: 700, marginBottom: '6px' }}>
          Group Members ({group.member_count} tracks)
        </div>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: '6px' }}>
          {group.member_track_ids.map((mid) => {
            const isSelected = mid === selectedTrackId;
            return (
              <button
                key={mid}
                type="button"
                onClick={() => onSelectTrack?.(mid)}
                className="btn btn-xs font-mono"
                style={{
                  padding: '3px 8px',
                  backgroundColor: isSelected ? 'var(--status-info, #0284c7)' : 'var(--bg-canvas, #0f172a)',
                  color: isSelected ? '#ffffff' : 'var(--text-primary, #f8fafc)',
                  border: isSelected ? '1px solid #38bdf8' : '1px solid var(--border-subtle, #334155)',
                  cursor: 'pointer',
                  borderRadius: 'var(--radius-sm, 4px)',
                }}
              >
                {mid}
              </button>
            );
          })}
        </div>
      </div>
    </div>
  );
};
