import React from 'react';
import { WorkspaceFilterState } from '../../types';
import { Button } from '../common/Button';

interface WorkspaceFilterBarProps {
  filters: WorkspaceFilterState;
  onChange: (filters: WorkspaceFilterState) => void;
  onReset: () => void;
}

export const WorkspaceFilterBar: React.FC<WorkspaceFilterBarProps> = ({
  filters,
  onChange,
  onReset,
}) => {
  const isFiltered =
    filters.trackState !== 'ALL' ||
    filters.alertSeverity !== 'ALL' ||
    filters.threatLevel !== 'ALL' ||
    filters.searchQuery.trim() !== '';

  return (
    <div
      style={{
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        flexWrap: 'wrap',
        gap: 'var(--space-sm)',
        padding: 'var(--space-xs) var(--space-sm)',
        backgroundColor: 'var(--bg-surface)',
        border: '1px solid var(--border-medium)',
        borderRadius: 'var(--radius-sm)',
      }}
    >
      {/* Filters Left */}
      <div style={{ display: 'flex', alignItems: 'center', flexWrap: 'wrap', gap: 'var(--space-sm)' }}>
        {/* Search Query */}
        <div style={{ position: 'relative' }}>
          <input
            type="text"
            className="tactical-input font-mono"
            placeholder="Filter ID, class, keyword..."
            value={filters.searchQuery}
            onChange={(e) => onChange({ ...filters, searchQuery: e.target.value })}
            style={{ width: '220px', padding: '4px 8px', fontSize: '11px' }}
          />
        </div>

        {/* Track State Filter */}
        <select
          className="tactical-select font-mono"
          value={filters.trackState}
          onChange={(e) => onChange({ ...filters, trackState: e.target.value as WorkspaceFilterState['trackState'] })}
          style={{ padding: '4px 8px', fontSize: '11px' }}
        >
          <option value="ALL">STATE: ALL</option>
          <option value="ACTIVE">STATE: ACTIVE</option>
          <option value="STALE">STATE: STALE</option>
          <option value="LOST">STATE: LOST</option>
          <option value="NEW">STATE: NEW</option>
          <option value="ARCHIVED">STATE: ARCHIVED</option>
        </select>

        {/* Alert Severity Filter */}
        <select
          className="tactical-select font-mono"
          value={filters.alertSeverity}
          onChange={(e) => onChange({ ...filters, alertSeverity: e.target.value as WorkspaceFilterState['alertSeverity'] })}
          style={{ padding: '4px 8px', fontSize: '11px' }}
        >
          <option value="ALL">SEV: ALL</option>
          <option value="CRITICAL">SEV: CRITICAL</option>
          <option value="HIGH">SEV: HIGH</option>
          <option value="MEDIUM">SEV: MEDIUM</option>
          <option value="LOW">SEV: LOW</option>
        </select>

        {/* Threat Level Filter */}
        <select
          className="tactical-select font-mono"
          value={filters.threatLevel}
          onChange={(e) => onChange({ ...filters, threatLevel: e.target.value as WorkspaceFilterState['threatLevel'] })}
          style={{ padding: '4px 8px', fontSize: '11px' }}
        >
          <option value="ALL">THREAT: ALL</option>
          <option value="CRITICAL">THREAT: CRITICAL</option>
          <option value="HIGH">THREAT: HIGH</option>
          <option value="MEDIUM">THREAT: MEDIUM</option>
          <option value="LOW">THREAT: LOW</option>
          <option value="NONE">THREAT: NONE</option>
        </select>
      </div>

      {/* Reset Filter Button */}
      {isFiltered && (
        <Button variant="ghost" size="sm" onClick={onReset} style={{ padding: '3px 8px', fontSize: '11px' }}>
          Reset Filters
        </Button>
      )}
    </div>
  );
};
