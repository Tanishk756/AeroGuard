import React, { useMemo, useState } from 'react';
import { useOperationalData } from '../../hooks/useOperationalData';
import { useTrackHistory } from '../../hooks/useTrackHistory';
import { useWorkspaceSelection } from '../../hooks/useWorkspaceSelection';
import { TimelineItem, Track, WorkspaceFilterState } from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { WorkspaceInspector } from '../inspector/WorkspaceInspector';
import { TacticalMap } from '../map/TacticalMap';
import { AlertPanel } from './AlertPanel';
import { GeofencePanel } from './GeofencePanel';
import { SensorPanel } from './SensorPanel';
import { ThreatPanel } from './ThreatPanel';
import { TimelinePanel } from './TimelinePanel';
import { TrackPanel } from './TrackPanel';
import { WorkspaceFilterBar } from './WorkspaceFilterBar';

type RegistryTab = 'tracks' | 'alerts' | 'threats' | 'sensors' | 'geofences' | 'timeline';

export const OperationalWorkspace: React.FC = () => {
  const {
    tracks,
    sensors,
    geofences,
    alerts,
    threats,
    timeline,
    lastUpdated,
    isLoading,
    isRefreshing,
    isStale,
    error,
    refresh,
  } = useOperationalData();

  const {
    selectedEntity,
    selectedTrackId,
    selectedSensorId,
    selectedGeofenceId,
    selectedAlertId,
    selectedThreatId,
    selectTrack,
    selectSensor,
    selectGeofence,
    selectAlert,
    selectThreat,
    clearSelection,
  } = useWorkspaceSelection();

  // Dedicated history hook reacting to selected track ID (Correction 1)
  const { historyPoints: selectedTrackHistory, isLoading: isHistoryLoading } =
    useTrackHistory(selectedTrackId);

  const [activeTab, setActiveTab] = useState<RegistryTab>('tracks');
  const [isInspectorOpen, setIsInspectorOpen] = useState<boolean>(true);

  // Workspace filtering state
  const [filters, setFilters] = useState<WorkspaceFilterState>({
    trackState: 'ALL',
    trackClassification: '',
    minConfidence: 0,
    sensorStatus: 'ALL',
    sensorModality: 'ALL',
    alertSeverity: 'ALL',
    alertStatus: 'ALL',
    threatLevel: 'ALL',
    searchQuery: '',
  });

  const resetFilters = () => {
    setFilters({
      trackState: 'ALL',
      trackClassification: '',
      minConfidence: 0,
      sensorStatus: 'ALL',
      sensorModality: 'ALL',
      alertSeverity: 'ALL',
      alertStatus: 'ALL',
      threatLevel: 'ALL',
      searchQuery: '',
    });
  };

  // Filtered operational datasets (Client-side presentation filters)
  const filteredTracks = useMemo(() => {
    return tracks.filter((t) => {
      if (filters.trackState !== 'ALL' && t.state !== filters.trackState) return false;
      if (filters.searchQuery.trim()) {
        const query = filters.searchQuery.toLowerCase();
        const matchesId = t.id.toLowerCase().includes(query);
        const matchesClass = (t.classification || '').toLowerCase().includes(query);
        if (!matchesId && !matchesClass) return false;
      }
      return true;
    });
  }, [tracks, filters.trackState, filters.searchQuery]);

  const filteredAlerts = useMemo(() => {
    return alerts.filter((a) => {
      if (filters.alertSeverity !== 'ALL' && a.severity !== filters.alertSeverity) return false;
      if (filters.searchQuery.trim()) {
        const query = filters.searchQuery.toLowerCase();
        const matchesType = a.type.toLowerCase().includes(query);
        const matchesReason = a.reason.toLowerCase().includes(query);
        const matchesTrack = (a.track_id || '').toLowerCase().includes(query);
        if (!matchesType && !matchesReason && !matchesTrack) return false;
      }
      return true;
    });
  }, [alerts, filters.alertSeverity, filters.searchQuery]);

  const filteredThreats = useMemo(() => {
    return threats.filter((th) => {
      if (filters.threatLevel !== 'ALL' && th.level !== filters.threatLevel) return false;
      if (filters.searchQuery.trim()) {
        const query = filters.searchQuery.toLowerCase();
        const matchesTrack = th.track_id.toLowerCase().includes(query);
        if (!matchesTrack) return false;
      }
      return true;
    });
  }, [threats, filters.threatLevel, filters.searchQuery]);

  const filteredSensors = useMemo(() => {
    return sensors.filter((s) => {
      if (filters.searchQuery.trim()) {
        const query = filters.searchQuery.toLowerCase();
        const matchesName = s.name.toLowerCase().includes(query);
        const matchesType = s.source_type.toLowerCase().includes(query);
        if (!matchesName && !matchesType) return false;
      }
      return true;
    });
  }, [sensors, filters.searchQuery]);

  const filteredGeofences = useMemo(() => {
    return geofences.filter((g) => {
      if (filters.searchQuery.trim()) {
        const query = filters.searchQuery.toLowerCase();
        return g.name.toLowerCase().includes(query);
      }
      return true;
    });
  }, [geofences, filters.searchQuery]);

  const handleTimelineSelect = (item: TimelineItem) => {
    if (item.track_id) {
      selectTrack(item.track_id);
    } else if (item.entity_id) {
      const isTrack = tracks.some((t) => t.id === item.entity_id);
      const isSensor = sensors.some((s) => s.id === item.entity_id);
      const isGeofence = geofences.some((g) => g.id === item.entity_id);
      if (isTrack) selectTrack(item.entity_id);
      else if (isSensor) selectSensor(item.entity_id);
      else if (isGeofence) selectGeofence(item.entity_id);
    }
  };

  const activeTracksCount = tracks.filter((t) => t.state === 'ACTIVE' || t.state === 'NEW').length;
  const openAlertsCount = alerts.filter((a) => a.status === 'OPEN').length;
  const elevatedThreatsCount = threats.filter((th) => th.level === 'HIGH' || th.level === 'CRITICAL').length;
  const onlineSensorsCount = sensors.filter((s) => s.status === 'ACTIVE').length;

  return (
    <div
      style={{
        padding: 'var(--space-md)',
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-md)',
        flex: 1,
        overflow: 'auto',
      }}
    >
      {/* Top Telemetry KPI Bar */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: 'var(--space-sm)',
        }}
      >
        <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
          <div className="uppercase-tracking text-muted" style={{ fontSize: '10px' }}>Active Tracks</div>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: '4px' }}>
            <span className="font-mono" style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--color-accent)' }}>
              {activeTracksCount}
            </span>
            <span className="font-mono text-xs text-muted">TOTAL: {tracks.length}</span>
          </div>
        </Card>

        <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
          <div className="uppercase-tracking text-muted" style={{ fontSize: '10px' }}>Open Alerts</div>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: '4px' }}>
            <span
              className="font-mono"
              style={{
                fontSize: 'var(--text-xl)',
                fontWeight: 700,
                color: openAlertsCount > 0 ? 'var(--status-critical)' : 'var(--status-success)',
              }}
            >
              {openAlertsCount}
            </span>
            <span className="font-mono text-xs text-muted">TOTAL: {alerts.length}</span>
          </div>
        </Card>

        <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
          <div className="uppercase-tracking text-muted" style={{ fontSize: '10px' }}>Elevated Threats</div>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: '4px' }}>
            <span
              className="font-mono"
              style={{
                fontSize: 'var(--text-xl)',
                fontWeight: 700,
                color: elevatedThreatsCount > 0 ? 'var(--status-warning)' : 'var(--text-secondary)',
              }}
            >
              {elevatedThreatsCount}
            </span>
            <span className="font-mono text-xs text-muted">TRIAGED: {threats.length}</span>
          </div>
        </Card>

        <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
          <div className="uppercase-tracking text-muted" style={{ fontSize: '10px' }}>Online Sensors</div>
          <div style={{ display: 'flex', alignItems: 'baseline', justifyContent: 'space-between', marginTop: '4px' }}>
            <span className="font-mono" style={{ fontSize: 'var(--text-xl)', fontWeight: 700, color: 'var(--status-success)' }}>
              {onlineSensorsCount}
            </span>
            <span className="font-mono text-xs text-muted">CONFIGURED: {sensors.length}</span>
          </div>
        </Card>
      </div>

      {/* Freshness & Stale Status Bar */}
      <div
        style={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 'var(--space-sm)',
          padding: '4px 8px',
          backgroundColor: isStale ? 'var(--status-warning-bg)' : 'var(--bg-surface)',
          border: isStale ? '1px solid var(--status-warning-border)' : '1px solid var(--border-subtle)',
          borderRadius: 'var(--radius-sm)',
        }}
      >
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-md)' }}>
          <span className="font-mono text-xs" style={{ color: isStale ? '#fcd34d' : 'var(--text-secondary)' }}>
            DATA STATE:{' '}
            <strong>
              {isLoading
                ? 'INITIALIZING TELEMETRY...'
                : isStale
                ? 'STALE (TRANSIENT REFRESH ERROR)'
                : isRefreshing
                ? 'REFRESHING...'
                : 'SYNCHRONIZED'}
            </strong>
          </span>

          {lastUpdated && (
            <span className="font-mono text-xs text-muted">
              LAST UPDATE: {lastUpdated.toISOString().substring(11, 19)} UTC
            </span>
          )}

          {error && <span className="font-mono text-xs" style={{ color: '#fca5a5' }}>({error})</span>}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          <Button
            variant="secondary"
            size="sm"
            onClick={refresh}
            isLoading={isRefreshing || isLoading}
            style={{ padding: '3px 8px', fontSize: '11px' }}
          >
            Refresh Operational Data
          </Button>

          <Button
            variant="ghost"
            size="sm"
            onClick={() => setIsInspectorOpen((prev) => !prev)}
            style={{ padding: '3px 8px', fontSize: '11px' }}
          >
            {isInspectorOpen ? 'Hide Inspector ⇥' : 'Show Inspector ⇤'}
          </Button>
        </div>
      </div>

      {/* Filter Toolbar */}
      <WorkspaceFilterBar
        filters={filters}
        onChange={setFilters}
        onReset={resetFilters}
      />

      {/* Main Operational Split Workspace: Map + Inspector */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: isInspectorOpen ? 'minmax(400px, 2fr) minmax(320px, 1fr)' : '1fr',
          gap: 'var(--space-md)',
          minHeight: '440px',
        }}
      >
        {/* Tactical Map */}
        <div style={{ height: '100%', minHeight: '440px' }}>
          <TacticalMap
            tracks={filteredTracks}
            sensors={filteredSensors}
            geofences={filteredGeofences}
            selectedTrackHistory={selectedTrackHistory}
            selectedTrackId={selectedTrackId}
            selectedSensorId={selectedSensorId}
            selectedGeofenceId={selectedGeofenceId}
            onSelectTrack={selectTrack}
            onSelectSensor={selectSensor}
            onSelectGeofence={selectGeofence}
            onClearSelection={clearSelection}
          />
        </div>

        {/* Workspace Inspector */}
        {isInspectorOpen && (
          <div style={{ overflowY: 'auto', maxHeight: '540px' }}>
            <WorkspaceInspector
              selectedEntity={selectedEntity}
              tracks={tracks}
              sensors={sensors}
              geofences={geofences}
              alerts={alerts}
              threats={threats}
              selectedTrackHistory={selectedTrackHistory}
              isHistoryLoading={isHistoryLoading}
              onClearSelection={clearSelection}
              onSelectTrack={selectTrack}
              onSelectAlert={selectAlert}
            />
          </div>
        )}
      </div>

      {/* Bottom Tabbed Operational Registry */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-xs)' }}>
        {/* Registry Tab Navigation */}
        <div style={{ display: 'flex', gap: '4px', borderBottom: '1px solid var(--border-medium)', paddingBottom: '2px' }}>
          <button
            className="tactical-btn"
            onClick={() => setActiveTab('tracks')}
            style={{
              backgroundColor: activeTab === 'tracks' ? 'var(--bg-surface-active)' : 'transparent',
              color: activeTab === 'tracks' ? 'var(--color-accent)' : 'var(--text-secondary)',
              borderColor: activeTab === 'tracks' ? 'var(--color-accent)' : 'transparent',
              padding: '5px 10px',
              fontSize: '11px',
            }}
          >
            Tracks ({filteredTracks.length})
          </button>
          <button
            className="tactical-btn"
            onClick={() => setActiveTab('alerts')}
            style={{
              backgroundColor: activeTab === 'alerts' ? 'var(--bg-surface-active)' : 'transparent',
              color: activeTab === 'alerts' ? 'var(--color-accent)' : 'var(--text-secondary)',
              borderColor: activeTab === 'alerts' ? 'var(--color-accent)' : 'transparent',
              padding: '5px 10px',
              fontSize: '11px',
            }}
          >
            Alerts ({filteredAlerts.length})
          </button>
          <button
            className="tactical-btn"
            onClick={() => setActiveTab('threats')}
            style={{
              backgroundColor: activeTab === 'threats' ? 'var(--bg-surface-active)' : 'transparent',
              color: activeTab === 'threats' ? 'var(--color-accent)' : 'var(--text-secondary)',
              borderColor: activeTab === 'threats' ? 'var(--color-accent)' : 'transparent',
              padding: '5px 10px',
              fontSize: '11px',
            }}
          >
            Threat Triage ({filteredThreats.length})
          </button>
          <button
            className="tactical-btn"
            onClick={() => setActiveTab('sensors')}
            style={{
              backgroundColor: activeTab === 'sensors' ? 'var(--bg-surface-active)' : 'transparent',
              color: activeTab === 'sensors' ? 'var(--color-accent)' : 'var(--text-secondary)',
              borderColor: activeTab === 'sensors' ? 'var(--color-accent)' : 'transparent',
              padding: '5px 10px',
              fontSize: '11px',
            }}
          >
            Sensors ({filteredSensors.length})
          </button>
          <button
            className="tactical-btn"
            onClick={() => setActiveTab('geofences')}
            style={{
              backgroundColor: activeTab === 'geofences' ? 'var(--bg-surface-active)' : 'transparent',
              color: activeTab === 'geofences' ? 'var(--color-accent)' : 'var(--text-secondary)',
              borderColor: activeTab === 'geofences' ? 'var(--color-accent)' : 'transparent',
              padding: '5px 10px',
              fontSize: '11px',
            }}
          >
            Geofences ({filteredGeofences.length})
          </button>
          <button
            className="tactical-btn"
            onClick={() => setActiveTab('timeline')}
            style={{
              backgroundColor: activeTab === 'timeline' ? 'var(--bg-surface-active)' : 'transparent',
              color: activeTab === 'timeline' ? 'var(--color-accent)' : 'var(--text-secondary)',
              borderColor: activeTab === 'timeline' ? 'var(--color-accent)' : 'transparent',
              padding: '5px 10px',
              fontSize: '11px',
            }}
          >
            Timeline ({timeline.length})
          </button>
        </div>

        {/* Tab Content */}
        {activeTab === 'tracks' && (
          <TrackPanel
            tracks={filteredTracks}
            selectedTrackId={selectedTrackId}
            onSelectTrack={selectTrack}
            isLoading={isLoading}
            error={error}
            onRefresh={refresh}
          />
        )}

        {activeTab === 'alerts' && (
          <AlertPanel
            alerts={filteredAlerts}
            selectedAlertId={selectedAlertId}
            onSelectAlert={selectAlert}
            isLoading={isLoading}
            error={error}
            onRefresh={refresh}
          />
        )}

        {activeTab === 'threats' && (
          <ThreatPanel
            threats={filteredThreats}
            selectedThreatId={selectedThreatId}
            onSelectThreat={selectThreat}
            isLoading={isLoading}
            error={error}
            onRefresh={refresh}
          />
        )}

        {activeTab === 'sensors' && (
          <SensorPanel
            sensors={filteredSensors}
            selectedSensorId={selectedSensorId}
            onSelectSensor={selectSensor}
            isLoading={isLoading}
            error={error}
            onRefresh={refresh}
          />
        )}

        {activeTab === 'geofences' && (
          <GeofencePanel
            geofences={filteredGeofences}
            selectedGeofenceId={selectedGeofenceId}
            onSelectGeofence={selectGeofence}
            isLoading={isLoading}
            error={error}
            onRefresh={refresh}
          />
        )}

        {activeTab === 'timeline' && (
          <TimelinePanel
            timeline={timeline}
            onSelectEvent={handleTimelineSelect}
            isLoading={isLoading}
            error={error}
            onRefresh={refresh}
          />
        )}
      </div>
    </div>
  );
};
