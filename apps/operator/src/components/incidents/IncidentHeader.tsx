/**
 * AeroGuard Incident Detail Header Component
 * Stage IM1-E: Operator Incident Workspace
 */

import React from 'react';
import { Incident } from '../../types';
import { StatusBadge } from '../common/StatusBadge';
import { getSeverityColor, getStatusBadgeVariant } from './IncidentList';

export interface IncidentHeaderProps {
  incident: Incident;
}

export const IncidentHeader: React.FC<IncidentHeaderProps> = ({ incident }) => {
  const sevColor = getSeverityColor(incident.severity);

  return (
    <div
      style={{
        padding: '16px 20px',
        backgroundColor: 'var(--bg-surface-elevated, #1a2333)',
        borderBottom: '1px solid var(--border-medium, #334155)',
        display: 'flex',
        flexDirection: 'column',
        gap: '12px',
      }}
    >
      {/* Top Row: Incident Number & Status Badges */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <span
            className="font-mono"
            style={{
              fontSize: '18px',
              fontWeight: 800,
              letterSpacing: '0.04em',
              color: 'var(--text-primary, #f8fafc)',
            }}
          >
            {incident.incident_number}
          </span>
          <span
            className="font-mono text-xs font-bold"
            style={{
              color: sevColor,
              padding: '2px 8px',
              borderRadius: '4px',
              border: `1px solid ${sevColor}`,
              backgroundColor: 'rgba(0, 0, 0, 0.3)',
            }}
          >
            {incident.severity} SEVERITY
          </span>
          <StatusBadge status={incident.status} />
        </div>

        <div className="font-mono text-xs text-muted" style={{ display: 'flex', gap: '12px' }}>
          <span>SRC: <strong style={{ color: 'var(--text-secondary, #cbd5e1)' }}>{incident.source}</strong></span>
          {incident.assigned_to && (
            <span>ASSIGNED: <strong style={{ color: 'var(--accent-primary, #3b82f6)' }}>{incident.assigned_to}</strong></span>
          )}
        </div>
      </div>

      {/* Incident Title */}
      <div>
        <h2
          style={{
            margin: 0,
            fontSize: '16px',
            fontWeight: 700,
            color: 'var(--text-primary, #f8fafc)',
            lineHeight: 1.3,
          }}
        >
          {incident.title}
        </h2>
        {incident.description && (
          <p
            style={{
              margin: '4px 0 0',
              fontSize: '13px',
              color: 'var(--text-secondary, #94a3b8)',
              lineHeight: 1.4,
            }}
          >
            {incident.description}
          </p>
        )}
      </div>

      {/* Metadata Timestamps Bar */}
      <div
        className="font-mono text-xs text-muted"
        style={{
          display: 'flex',
          alignItems: 'center',
          gap: '16px',
          flexWrap: 'wrap',
          borderTop: '1px solid var(--border-subtle, #273549)',
          paddingTop: '8px',
        }}
      >
        <span>CREATED: {new Date(incident.created_at).toLocaleString()}</span>
        <span>UPDATED: {new Date(incident.updated_at).toLocaleString()}</span>
        {incident.acknowledged_at && (
          <span>ACK: {new Date(incident.acknowledged_at).toLocaleTimeString()}</span>
        )}
        {incident.resolved_at && (
          <span>RESOLVED: {new Date(incident.resolved_at).toLocaleTimeString()}</span>
        )}
        {incident.closed_at && (
          <span>CLOSED: {new Date(incident.closed_at).toLocaleTimeString()}</span>
        )}
      </div>
    </div>
  );
};
