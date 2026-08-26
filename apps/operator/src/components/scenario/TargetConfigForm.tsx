import React from 'react';
import { ScenarioTargetDefinition, ScenarioWaypoint } from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';

interface TargetConfigFormProps {
  targets: ScenarioTargetDefinition[];
  onChange: (targets: ScenarioTargetDefinition[]) => void;
}

export const TargetConfigForm: React.FC<TargetConfigFormProps> = ({ targets, onChange }) => {
  const handleAddTarget = () => {
    const nextIdx = targets.length + 1;
    const newTarget: ScenarioTargetDefinition = {
      target_id: `TARGET-${nextIdx}`,
      classification: 'DRONE_ROTARY',
      initial_latitude: 37.7749,
      initial_longitude: -122.4194,
      initial_altitude: 120.0,
      velocity: 15.0,
      heading: 90.0,
      waypoints: [],
    };
    onChange([...targets, newTarget]);
  };

  const handleRemoveTarget = (index: number) => {
    onChange(targets.filter((_, idx) => idx !== index));
  };

  const handleUpdateTarget = (index: number, patch: Partial<ScenarioTargetDefinition>) => {
    const updated = targets.map((t, idx) => (idx === index ? { ...t, ...patch } : t));
    onChange(updated);
  };

  const handleAddWaypoint = (targetIndex: number) => {
    const target = targets[targetIndex];
    const lastWp = target.waypoints[target.waypoints.length - 1];
    const newWp: ScenarioWaypoint = {
      latitude: lastWp ? lastWp.latitude + 0.005 : target.initial_latitude + 0.005,
      longitude: lastWp ? lastWp.longitude + 0.005 : target.initial_longitude + 0.005,
      altitude: lastWp ? lastWp.altitude : target.initial_altitude,
      speed: target.velocity,
    };
    handleUpdateTarget(targetIndex, {
      waypoints: [...target.waypoints, newWp],
    });
  };

  const handleRemoveWaypoint = (targetIndex: number, wpIndex: number) => {
    const target = targets[targetIndex];
    handleUpdateTarget(targetIndex, {
      waypoints: target.waypoints.filter((_, idx) => idx !== wpIndex),
    });
  };

  const handleUpdateWaypoint = (
    targetIndex: number,
    wpIndex: number,
    patch: Partial<ScenarioWaypoint>
  ) => {
    const target = targets[targetIndex];
    const updatedWps = target.waypoints.map((wp, idx) =>
      idx === wpIndex ? { ...wp, ...patch } : wp
    );
    handleUpdateTarget(targetIndex, { waypoints: updatedWps });
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h3 className="font-mono text-xs uppercase-tracking" style={{ margin: 0, fontWeight: 700, color: 'var(--color-accent)' }}>
            Synthetic Target Drones ({targets.length})
          </h3>
          <p className="text-muted" style={{ margin: '2px 0 0', fontSize: '10px' }}>
            Define simulated drone kinematics and trajectory paths (constant velocity or waypoints).
          </p>
        </div>
        <Button variant="primary" size="sm" type="button" onClick={handleAddTarget} style={{ padding: '2px 8px', fontSize: '11px' }}>
          + Add Target
        </Button>
      </div>

      {targets.length === 0 ? (
        <div style={{ padding: '16px', textAlign: 'center', backgroundColor: 'var(--bg-canvas)', borderRadius: 'var(--radius-sm)', border: '1px dashed var(--border-subtle)' }}>
          <p className="text-muted text-xs font-mono" style={{ margin: 0 }}>
            No synthetic targets configured. Click '+ Add Target' to add simulated drones.
          </p>
        </div>
      ) : (
        targets.map((target, tIdx) => (
          <Card
            key={`target-${tIdx}`}
            title={`Target #${tIdx + 1}: ${target.target_id}`}
            actions={
              <Button
                variant="ghost"
                size="sm"
                type="button"
                onClick={() => handleRemoveTarget(tIdx)}
                style={{ color: 'var(--status-critical)', padding: '1px 6px', fontSize: '10px' }}
              >
                ✕ Remove Target
              </Button>
            }
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {/* Row 1: Target Identity & Classification */}
              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1.2fr 1fr 1fr', gap: '8px' }}>
                <div>
                  <label className="text-muted text-xs uppercase-tracking">Target ID *</label>
                  <input
                    type="text"
                    className="tactical-input font-mono"
                    value={target.target_id}
                    onChange={(e) => handleUpdateTarget(tIdx, { target_id: e.target.value.toUpperCase() })}
                    placeholder="TARGET-01"
                    required
                  />
                </div>

                <div>
                  <label className="text-muted text-xs uppercase-tracking">Classification</label>
                  <select
                    className="tactical-select font-mono"
                    value={target.classification || 'DRONE_ROTARY'}
                    onChange={(e) => handleUpdateTarget(tIdx, { classification: e.target.value })}
                  >
                    <option value="DRONE_ROTARY">DRONE_ROTARY (Quadcopter/Hex)</option>
                    <option value="DRONE_FIXED_WING">DRONE_FIXED_WING</option>
                    <option value="UNKNOWN_UAV">UNKNOWN_UAV</option>
                    <option value="COMMERCIAL_DRONE">COMMERCIAL_DRONE</option>
                  </select>
                </div>

                <div>
                  <label className="text-muted text-xs uppercase-tracking">Speed (m/s)</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    className="tactical-input font-mono"
                    value={target.velocity}
                    onChange={(e) => handleUpdateTarget(tIdx, { velocity: Math.max(0, parseFloat(e.target.value) || 0) })}
                    required
                  />
                </div>

                <div>
                  <label className="text-muted text-xs uppercase-tracking">Heading (° True)</label>
                  <input
                    type="number"
                    step="1"
                    min="0"
                    max="359.9"
                    className="tactical-input font-mono"
                    value={target.heading}
                    onChange={(e) => handleUpdateTarget(tIdx, { heading: (parseFloat(e.target.value) || 0) % 360 })}
                    required
                  />
                </div>
              </div>

              {/* Row 2: Initial Position Coordinates */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
                <div>
                  <label className="text-muted text-xs uppercase-tracking">Initial Latitude (°)</label>
                  <input
                    type="number"
                    step="0.0001"
                    className="tactical-input font-mono"
                    value={target.initial_latitude}
                    onChange={(e) => handleUpdateTarget(tIdx, { initial_latitude: parseFloat(e.target.value) || 0 })}
                    required
                  />
                </div>
                <div>
                  <label className="text-muted text-xs uppercase-tracking">Initial Longitude (°)</label>
                  <input
                    type="number"
                    step="0.0001"
                    className="tactical-input font-mono"
                    value={target.initial_longitude}
                    onChange={(e) => handleUpdateTarget(tIdx, { initial_longitude: parseFloat(e.target.value) || 0 })}
                    required
                  />
                </div>
                <div>
                  <label className="text-muted text-xs uppercase-tracking">Initial Altitude (m AGL)</label>
                  <input
                    type="number"
                    step="1"
                    min="0"
                    className="tactical-input font-mono"
                    value={target.initial_altitude ?? ''}
                    onChange={(e) => handleUpdateTarget(tIdx, { initial_altitude: e.target.value ? parseFloat(e.target.value) : null })}
                    placeholder="120"
                  />
                </div>
              </div>

              {/* Waypoints Section */}
              <div style={{ borderTop: '1px solid var(--border-subtle)', paddingTop: '8px' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '6px' }}>
                  <span className="font-mono text-xs text-muted uppercase-tracking">
                    Waypoints ({target.waypoints.length}) — {target.waypoints.length === 0 ? 'Constant-Velocity Vector' : 'Waypoint Trajectory Flight Path'}
                  </span>
                  <Button
                    variant="secondary"
                    size="sm"
                    type="button"
                    onClick={() => handleAddWaypoint(tIdx)}
                    style={{ padding: '1px 6px', fontSize: '10px' }}
                  >
                    + Add Waypoint
                  </Button>
                </div>

                {target.waypoints.length > 0 && (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', maxHeight: '140px', overflowY: 'auto' }}>
                    {target.waypoints.map((wp, wpIdx) => (
                      <div
                        key={`wp-${wpIdx}`}
                        style={{
                          display: 'grid',
                          gridTemplateColumns: '28px 1fr 1fr 1fr 1fr 24px',
                          gap: '6px',
                          alignItems: 'center',
                          backgroundColor: 'var(--bg-canvas)',
                          padding: '3px 6px',
                          borderRadius: 'var(--radius-sm)',
                        }}
                      >
                        <span className="font-mono text-xs text-muted">#{wpIdx + 1}</span>
                        <input
                          type="number"
                          step="0.0001"
                          className="tactical-input font-mono"
                          value={wp.latitude}
                          onChange={(e) => handleUpdateWaypoint(tIdx, wpIdx, { latitude: parseFloat(e.target.value) || 0 })}
                          placeholder="Lat"
                          required
                        />
                        <input
                          type="number"
                          step="0.0001"
                          className="tactical-input font-mono"
                          value={wp.longitude}
                          onChange={(e) => handleUpdateWaypoint(tIdx, wpIdx, { longitude: parseFloat(e.target.value) || 0 })}
                          placeholder="Lon"
                          required
                        />
                        <input
                          type="number"
                          step="1"
                          className="tactical-input font-mono"
                          value={wp.altitude ?? ''}
                          onChange={(e) => handleUpdateWaypoint(tIdx, wpIdx, { altitude: e.target.value ? parseFloat(e.target.value) : null })}
                          placeholder="Alt (m)"
                        />
                        <input
                          type="number"
                          step="0.5"
                          className="tactical-input font-mono"
                          value={wp.speed ?? ''}
                          onChange={(e) => handleUpdateWaypoint(tIdx, wpIdx, { speed: e.target.value ? parseFloat(e.target.value) : null })}
                          placeholder="Speed (m/s)"
                        />
                        <Button
                          variant="ghost"
                          size="sm"
                          type="button"
                          onClick={() => handleRemoveWaypoint(tIdx, wpIdx)}
                          style={{ padding: 0, height: '22px', color: 'var(--status-critical)' }}
                        >
                          ✕
                        </Button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </Card>
        ))
      )}
    </div>
  );
};
