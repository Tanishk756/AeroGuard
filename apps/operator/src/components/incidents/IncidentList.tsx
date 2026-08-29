/**
 * AeroGuard Incident List Component
 * Stage IM1-E: Operator Incident Workspace
 */

import React, { useMemo } from 'react';
import { Incident, IncidentFilterParams, IncidentSeverity, IncidentStatus } from '../../types';
import { StatusBadge } from '../common/StatusBadge';

export interface IncidentListProps {
  incidents: Incident[];
  selectedId: string | null;
  onSelect: (id: string) => void;
  isLoading: boolean;
  filters: IncidentFilterParams;
  onFilterChange: (filters: Partial<IncidentFilterParams>) => void;
  onOpenCreateModal?: () => void;
  canCreate?: boolean;
  onOpenExportModal?: () => void;
  canExport?: boolean;
}

export const getSeverityColor = (severity: IncidentSeverity): string => {
  switch (severity) {
    case 'CRITICAL':
      return 'var(--status-critical, #ef4444)';
    case 'HIGH':
      return 'var(--status-warning, #f59e0b)';
    case 'MEDIUM':
      return 'var(--accent-primary, #3b82f6)';
    case 'LOW':
    default:
      return 'var(--status-neutral, #6b7280)';
  }
};

export const getStatusBadgeVariant = (status: IncidentStatus) => {
  switch (status) {
    case 'NEW':
      return 'warning';
    case 'ACKNOWLEDGED':
    case 'TRIAGED':
      return 'info';
    case 'ESCALATED':
      return 'critical';
    case 'RESOLVED':
      return 'success';
    case 'CLOSED':
      return 'offline';
    default:
      return 'neutral';
  }
};

export const IncidentList: React.FC<IncidentListProps> = ({
  incidents,
  selectedId,
  onSelect,
  isLoading,
  filters,
  onFilterChange,
  onOpenCreateModal,
  canCreate = false,
  onOpenExportModal,
  canExport = false,
}) => {
  const filteredIncidents = useMemo(() => {
    return incidents.filter((inc) => {
      if (filters.search) {
        const q = filters.search.toLowerCase();
        const matchTitle = inc.title.toLowerCase().includes(q);
        const matchNum = inc.incident_number.toLowerCase().includes(q);
        const matchTrack = inc.primary_track_id?.toLowerCase().includes(q);
        const matchGroup = inc.primary_group_id?.toLowerCase().includes(q);
        if (!matchTitle && !matchNum && !matchTrack && !matchGroup) return false;
      }
      if (filters.status && inc.status !== filters.status) return false;
      if (filters.severity && inc.severity !== filters.severity) return false;
      if (filters.source && inc.source !== filters.source) return false;
      if (filters.assigned_to && inc.assigned_to !== filters.assigned_to) return false;
      return true;
    });
  }, [incidents, filters]);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100%',
        backgroundColor: 'var(--bg-surface, #1e293b)',
        borderRight: '1px solid var(--border-medium, #334155)',
        boxSizing: 'border-box',
      }}
    >
      {/* Header & Quick Action */}
      <div
        style={{
          padding: '12px',
          borderBottom: '1px solid var(--border-medium, #334155)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          gap: '8px',
        }}
      >
        <div>
          <span style={{ fontSize: '13px', fontWeight: 700, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
            Incidents
          </span>
          <span className="font-mono text-xs text-muted" style={{ marginLeft: '6px' }}>
            ({filteredIncidents.length})
          </span>
        </div>
        <div style={{ display: 'flex', gap: '6px' }}>
          {canExport && onOpenExportModal && (
            <button
              type="button"
              className="btn btn-secondary btn-sm font-mono"
              onClick={onOpenExportModal}
              aria-label="Export Incidents"
            >
              📥 Export
            </button>
          )}
          {canCreate && onOpenCreateModal && (
            <button
              type="button"
              className="btn btn-primary btn-sm font-mono"
              onClick={onOpenCreateModal}
              aria-label="Create New Incident"
            >
              + New Incident
            </button>
          )}
        </div>
      </div>

      {/* Search & Filters */}
      <div
        style={{
          padding: '10px 12px',
          borderBottom: '1px solid var(--border-medium, #334155)',
          display: 'flex',
          flexDirection: 'column',
          gap: '8px',
        }}
      >
        <input
          type="text"
          className="tactical-input font-mono text-xs"
          placeholder="Search number, title, track..."
          value={filters.search || ''}
          onChange={(e) => onFilterChange({ search: e.target.value })}
          aria-label="Search incidents"
        />

        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '6px' }}>
          <select
            className="tactical-select font-mono text-xs"
            value={filters.severity || ''}
            onChange={(e) => onFilterChange({ severity: e.target.value || undefined })}
            aria-label="Filter by severity"
          >
            <option value="">ALL SEVERITY</option>
            <option value="CRITICAL">CRITICAL</option>
            <option value="HIGH">HIGH</option>
            <option value="MEDIUM">MEDIUM</option>
            <option value="LOW">LOW</option>
          </select>

          <select
            className="tactical-select font-mono text-xs"
            value={filters.status || ''}
            onChange={(e) => onFilterChange({ status: e.target.value || undefined })}
            aria-label="Filter by status"
          >
            <option value="">ALL STATUS</option>
            <option value="NEW">NEW</option>
            <option value="ACKNOWLEDGED">ACKNOWLEDGED</option>
            <option value="TRIAGED">TRIAGED</option>
            <option value="ESCALATED">ESCALATED</option>
            <option value="RESOLVED">RESOLVED</option>
            <option value="CLOSED">CLOSED</option>
          </select>
        </div>
      </div>

      {/* Incident Item List */}
      <div
        style={{
          flex: 1,
          overflowY: 'auto',
          display: 'flex',
          flexDirection: 'column',
        }}
        role="list"
        aria-label="Incident List"
      >
        {isLoading && filteredIncidents.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center' }} className="text-muted font-mono text-xs">
            Loading incidents...
          </div>
        ) : filteredIncidents.length === 0 ? (
          <div style={{ padding: '24px', textAlign: 'center' }} className="text-muted font-mono text-xs">
            No matching incidents found.
          </div>
        ) : (
          filteredIncidents.map((inc) => {
            const isSelected = inc.id === selectedId;
            const sevColor = getSeverityColor(inc.severity);

            return (
              <div
                key={inc.id}
                role="listitem"
                tabIndex={0}
                onClick={() => onSelect(inc.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelect(inc.id);
                  }
                }}
                style={{
                  padding: '10px 12px',
                  borderBottom: '1px solid var(--border-subtle, #273549)',
                  borderLeft: `4px solid ${sevColor}`,
                  backgroundColor: isSelected ? 'var(--bg-surface-active, rgba(59, 130, 246, 0.15))' : 'transparent',
                  cursor: 'pointer',
                  transition: 'background-color 0.15s ease',
                }}
              >
                {/* Top Row: Incident Number, Severity, Status */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '4px' }}>
                  <span className="font-mono text-xs font-bold" style={{ color: 'var(--text-primary, #f8fafc)' }}>
                    {inc.incident_number}
                  </span>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <span
                      className="font-mono text-xs font-bold"
                      style={{
                        color: sevColor,
                        fontSize: '10px',
                        padding: '1px 4px',
                        borderRadius: '2px',
                        backgroundColor: 'rgba(0,0,0,0.3)',
                      }}
                    >
                      {inc.severity}
                    </span>
                    <StatusBadge status={inc.status} />
                  </div>
                </div>

                {/* Title */}
                <div
                  style={{
                    fontSize: '12px',
                    fontWeight: 600,
                    color: 'var(--text-primary, #f8fafc)',
                    marginBottom: '6px',
                    lineHeight: '1.3',
                  }}
                >
                  {inc.title}
                </div>

                {/* Footer Meta & Correlations */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', fontSize: '11px' }} className="font-mono text-muted">
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
                    {inc.primary_track_id && (
                      <span style={{ backgroundColor: 'rgba(59, 130, 246, 0.2)', padding: '1px 4px', borderRadius: '2px' }}>
                        {inc.primary_track_id}
                      </span>
                    )}
                    {inc.primary_group_id && (
                      <span style={{ backgroundColor: 'rgba(168, 85, 247, 0.2)', padding: '1px 4px', borderRadius: '2px' }}>
                        {inc.primary_group_id}
                      </span>
                    )}
                  </div>
                  <span>
                    {new Date(inc.updated_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>
              </div>
            );
          })
        )}
      </div>
    </div>
  );
};
