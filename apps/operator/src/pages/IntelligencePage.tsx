/**
 * AeroGuard Defensive AI Intelligence Workspace Page — Stage AI2-G
 */

import React, { useState } from 'react';
import { GroupIntelligencePanel } from '../components/intelligence/GroupIntelligencePanel';
import { IntelligenceSummary } from '../components/intelligence/IntelligenceSummary';
import { PriorityList } from '../components/intelligence/PriorityList';
import { TrackIntelligencePanel } from '../components/intelligence/TrackIntelligencePanel';
import { TacticalMap } from '../components/map/TacticalMap';
import { useIntelligence } from '../hooks/useIntelligence';
import { useOperationalData } from '../hooks/useOperationalData';

export const IntelligencePage: React.FC = () => {
  const { tracks, sensors, geofences, threats, intelligence: singleTrackIntel } = useOperationalData();
  const {
    summary,
    groups,
    priorities,
    selectedTrackId,
    selectedGroupId,
    isLoading,
    isRefreshing,
    error,
    setSelectedTrackId,
    setSelectedGroupId,
    refresh,
  } = useIntelligence();

  const [activeTab, setActiveTab] = useState<'priorities' | 'groups'>('priorities');

  const selectedTrack = selectedTrackId ? tracks.find((t) => t.id === selectedTrackId) : null;
  const selectedPriority = selectedTrackId ? priorities.find((p) => p.track_id === selectedTrackId) : null;
  const selectedBehavior = selectedTrackId ? summary?.behaviors.find((b) => b.track_id === selectedTrackId) : null;
  const selectedGroup = selectedGroupId
    ? groups.find((g) => g.group_id === selectedGroupId)
    : selectedTrackId
    ? groups.find((g) => g.member_track_ids.includes(selectedTrackId))
    : null;
  const selectedFormation = selectedGroup
    ? summary?.formations.find((f) => f.group_id === selectedGroup.group_id)
    : null;

  const handleSelectTrack = (trackId: string) => {
    setSelectedTrackId(trackId);
    const grp = groups.find((g) => g.member_track_ids.includes(trackId));
    setSelectedGroupId(grp ? grp.group_id : null);
  };

  const handleSelectGroup = (groupId: string) => {
    setSelectedGroupId(groupId);
    const grp = groups.find((g) => g.group_id === groupId);
    if (grp && grp.member_track_ids.length > 0) {
      setSelectedTrackId(grp.member_track_ids[0]);
    }
  };

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        gap: 'var(--space-md, 12px)',
        height: 'calc(100vh - 56px)',
        padding: 'var(--space-md, 12px)',
        overflow: 'hidden',
        boxSizing: 'border-box',
      }}
    >
      {/* Top Header & Refresh Control */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h2 style={{ margin: 0, fontSize: '18px', fontWeight: 700, letterSpacing: '-0.02em', color: 'var(--text-primary, #f8fafc)' }}>
            Defensive AI & Multi-Track Intelligence
          </h2>
          <span className="font-mono text-xs text-muted">
            Autonomous threat prioritization, behavioral classification, and formation correlation.
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <button
            type="button"
            onClick={() => refresh()}
            disabled={isLoading || isRefreshing}
            className="btn btn-secondary btn-sm font-mono"
            aria-label="Refresh intelligence evaluations"
          >
            {isRefreshing ? '↻ Evaluating...' : '↻ Refresh AI'}
          </button>
        </div>
      </div>

      {/* Situational Awareness Metrics Cards */}
      <IntelligenceSummary summary={summary} isLoading={isLoading} />

      {error && (
        <div
          role="alert"
          style={{
            padding: '8px 12px',
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            borderRadius: 'var(--radius-sm, 4px)',
            color: '#fca5a5',
            fontSize: '12px',
            fontFamily: 'var(--font-mono, monospace)',
          }}
        >
          ⚠ {error}
        </div>
      )}

      {/* Main Multi-Column Intelligence Layout */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '320px 1fr 340px',
          gap: 'var(--space-md, 12px)',
          flex: 1,
          minHeight: 0,
        }}
      >
        {/* Left Column: Priority Rankings & Group Switcher */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            backgroundColor: 'var(--bg-surface, #1e293b)',
            border: '1px solid var(--border-subtle, #334155)',
            borderRadius: 'var(--radius-md, 6px)',
            padding: '10px',
            overflow: 'hidden',
          }}
        >
          {/* Tab Navigation */}
          <div style={{ display: 'flex', borderBottom: '1px solid var(--border-subtle, #334155)', paddingBottom: '6px', gap: '4px' }}>
            <button
              type="button"
              onClick={() => setActiveTab('priorities')}
              className={`btn btn-xs font-mono ${activeTab === 'priorities' ? 'btn-primary' : 'btn-ghost'}`}
              style={{ flex: 1, fontWeight: 700 }}
            >
              Priorities ({priorities.length})
            </button>
            <button
              type="button"
              onClick={() => setActiveTab('groups')}
              className={`btn btn-xs font-mono ${activeTab === 'groups' ? 'btn-primary' : 'btn-ghost'}`}
              style={{ flex: 1, fontWeight: 700 }}
            >
              Groups ({groups.length})
            </button>
          </div>

          {/* Tab Content */}
          <div style={{ flex: 1, overflowY: 'auto' }}>
            {activeTab === 'priorities' ? (
              <PriorityList
                priorities={priorities}
                behaviors={summary?.behaviors}
                selectedTrackId={selectedTrackId}
                onSelectTrack={handleSelectTrack}
              />
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                {groups.length === 0 ? (
                  <div style={{ padding: '16px', textAlign: 'center', color: 'var(--text-muted, #94a3b8)', fontSize: '11px', fontFamily: 'var(--font-mono, monospace)' }}>
                    No correlated multi-track groups detected.
                  </div>
                ) : (
                  groups.map((g) => {
                    const isSelected = g.group_id === selectedGroupId;
                    return (
                      <div
                        key={g.group_id}
                        onClick={() => handleSelectGroup(g.group_id)}
                        role="button"
                        tabIndex={0}
                        onKeyDown={(e) => {
                          if (e.key === 'Enter' || e.key === ' ') {
                            e.preventDefault();
                            handleSelectGroup(g.group_id);
                          }
                        }}
                        style={{
                          padding: '8px 10px',
                          backgroundColor: isSelected ? 'rgba(192, 132, 252, 0.15)' : 'var(--bg-canvas, #0f172a)',
                          border: isSelected ? '1px solid #c084fc' : '1px solid var(--border-subtle, #334155)',
                          borderRadius: 'var(--radius-sm, 4px)',
                          cursor: 'pointer',
                        }}
                      >
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <span className="font-mono text-xs" style={{ fontWeight: 700, color: '#c084fc' }}>
                            {g.group_id}
                          </span>
                          <span className="font-mono text-xs text-muted">
                            {g.member_count} tracks
                          </span>
                        </div>
                        <div className="font-mono text-xs text-muted" style={{ fontSize: '10px', marginTop: '2px' }}>
                          Radius: ~{g.radius_meters.toFixed(0)}m • State: {g.behavioral_state}
                        </div>
                      </div>
                    );
                  })
                )}
              </div>
            )}
          </div>
        </div>

        {/* Center Column: Tactical Map with AI Overlays */}
        <div
          style={{
            position: 'relative',
            borderRadius: 'var(--radius-md, 6px)',
            overflow: 'hidden',
            border: '1px solid var(--border-subtle, #334155)',
          }}
        >
          <TacticalMap
            tracks={tracks}
            threats={threats}
            intelligence={singleTrackIntel}
            multiTrackIntelligence={summary}
            sensors={sensors}
            geofences={geofences}
            selectedTrackId={selectedTrackId}
            selectedGroupId={selectedGroupId}
            onSelectTrack={handleSelectTrack}
            onSelectGroup={handleSelectGroup}
            onClearSelection={() => {
              setSelectedTrackId(null);
              setSelectedGroupId(null);
            }}
          />
        </div>

        {/* Right Column: Detailed Track or Group Inspector */}
        <div
          style={{
            display: 'flex',
            flexDirection: 'column',
            gap: '8px',
            overflowY: 'auto',
          }}
        >
          {selectedTrackId ? (
            <TrackIntelligencePanel
              trackId={selectedTrackId}
              priority={selectedPriority}
              behavior={selectedBehavior}
              group={selectedGroup}
              formation={selectedFormation}
              intelligence={singleTrackIntel[selectedTrackId]}
              onSelectGroup={handleSelectGroup}
            />
          ) : selectedGroup ? (
            <GroupIntelligencePanel
              group={selectedGroup}
              formation={selectedFormation}
              selectedTrackId={selectedTrackId}
              onSelectTrack={handleSelectTrack}
            />
          ) : (
            <div
              style={{
                padding: '24px',
                textAlign: 'center',
                backgroundColor: 'var(--bg-surface, #1e293b)',
                border: '1px solid var(--border-subtle, #334155)',
                borderRadius: 'var(--radius-md, 6px)',
                color: 'var(--text-muted, #94a3b8)',
                fontFamily: 'var(--font-mono, monospace)',
                fontSize: '12px',
              }}
            >
              Select an airspace track from the priority rankings or map to inspect defensive intelligence telemetry.
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
