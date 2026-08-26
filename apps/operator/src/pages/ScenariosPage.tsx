import React, { useState } from 'react';
import { Card } from '../components/common/Card';
import { EmptyState } from '../components/common/EmptyState';
import { ScenarioPanel } from '../components/workspace/ScenarioPanel';
import { Scenario } from '../types';

export const ScenariosPage: React.FC = () => {
  const [selectedScenario, setSelectedScenario] = useState<Scenario | null>(null);

  const targets = (selectedScenario?.configuration_metadata?.targets as unknown[]) || [];
  const sensors = (selectedScenario?.configuration_metadata?.sensors as unknown[]) || [];
  const geofenceIds = (selectedScenario?.configuration_metadata?.geofence_ids as string[]) || [];

  return (
    <div style={{ padding: 'var(--space-md)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', flex: 1 }}>
      {/* Header */}
      <div>
        <h1 style={{ fontSize: 'var(--text-lg)', textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0 }}>
          Scenario Simulation & Execution Hub (F5 Engine)
        </h1>
        <p className="text-muted text-xs" style={{ margin: '2px 0 0' }}>
          Deterministic discrete simulation stepping, virtual clock management, synthetic target trajectories, and sensor FOV simulation.
        </p>
      </div>

      {/* Main Execution Hub */}
      <ScenarioPanel onSelectScenario={setSelectedScenario} />

      {/* Scenario Composition Details */}
      {selectedScenario && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: 'var(--space-md)' }}>
          <Card title="Synthetic Target Definitions" badge={<span className="font-mono text-xs text-muted">{targets.length} TARGETS</span>}>
            {targets.length === 0 ? (
              <EmptyState title="No Targets" description="No synthetic targets configured in this scenario." />
            ) : (
              <div className="tactical-table-wrapper" style={{ maxHeight: '200px' }}>
                <table className="tactical-table">
                  <thead>
                    <tr>
                      <th>Target ID</th>
                      <th>Class</th>
                      <th>Vel (m/s)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {targets.map((t: any, idx: number) => (
                      <tr key={t.target_id || idx}>
                        <td className="font-mono" style={{ fontWeight: 600 }}>{t.target_id}</td>
                        <td className="uppercase-tracking text-xs">{t.classification || 'Synthetic'}</td>
                        <td className="font-mono text-xs">{t.velocity != null ? t.velocity : 0}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Card title="Synthetic Sensor Modalities" badge={<span className="font-mono text-xs text-muted">{sensors.length} SENSORS</span>}>
            {sensors.length === 0 ? (
              <EmptyState title="No Sensors" description="No synthetic sensors configured in this scenario." />
            ) : (
              <div className="tactical-table-wrapper" style={{ maxHeight: '200px' }}>
                <table className="tactical-table">
                  <thead>
                    <tr>
                      <th>Sensor ID</th>
                      <th>Modality</th>
                      <th>Range</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sensors.map((s: any, idx: number) => (
                      <tr key={s.sensor_id || idx}>
                        <td className="font-mono" style={{ fontWeight: 600 }}>{s.sensor_id}</td>
                        <td className="uppercase-tracking text-xs" style={{ color: 'var(--color-accent)' }}>{s.modality}</td>
                        <td className="font-mono text-xs">{s.range_meters ? `${s.range_meters}m` : 'N/A'}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </Card>

          <Card title="Active Geofence Boundaries" badge={<span className="font-mono text-xs text-muted">{geofenceIds.length} ZONES</span>}>
            {geofenceIds.length === 0 ? (
              <p className="font-mono text-xs text-muted" style={{ padding: 'var(--space-sm)' }}>
                No specific geofence boundaries assigned.
              </p>
            ) : (
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-xs)', padding: 'var(--space-xs)' }}>
                {geofenceIds.map((gid) => (
                  <span
                    key={gid}
                    className="font-mono text-xs"
                    style={{
                      padding: '3px 8px',
                      backgroundColor: 'var(--bg-canvas)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      color: 'var(--text-secondary)',
                    }}
                  >
                    ZONE: {gid}
                  </span>
                ))}
              </div>
            )}
          </Card>
        </div>
      )}
    </div>
  );
};
