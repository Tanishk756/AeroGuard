import React from 'react';
import { ScenarioSensorDefinition } from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';

interface SensorConfigFormProps {
  sensors: ScenarioSensorDefinition[];
  onChange: (sensors: ScenarioSensorDefinition[]) => void;
}

export const SensorConfigForm: React.FC<SensorConfigFormProps> = ({ sensors, onChange }) => {
  const handleAddSensor = () => {
    const nextIdx = sensors.length + 1;
    const newSensor: ScenarioSensorDefinition = {
      sensor_id: `SIM-SENSOR-${nextIdx}`,
      modality: 'radar',
      latitude: 37.7749,
      longitude: -122.4194,
      altitude: 10.0,
      range_meters: 5000.0,
      detection_probability: 0.95,
      position_uncertainty_meters: 5.0,
      fov_azimuth_start_deg: 0,
      fov_azimuth_span_deg: 360,
    };
    onChange([...sensors, newSensor]);
  };

  const handleRemoveSensor = (index: number) => {
    onChange(sensors.filter((_, idx) => idx !== index));
  };

  const handleUpdateSensor = (index: number, patch: Partial<ScenarioSensorDefinition>) => {
    const updated = sensors.map((s, idx) => (idx === index ? { ...s, ...patch } : s));
    onChange(updated);
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
        <div>
          <h3 className="font-mono text-xs uppercase-tracking" style={{ margin: 0, fontWeight: 700, color: 'var(--color-accent)' }}>
            Synthetic Sensor Assets ({sensors.length})
          </h3>
          <p className="text-muted" style={{ margin: '2px 0 0', fontSize: '10px' }}>
            Configure synthetic Radar, Optical, and RF sensor modalities, FOV gating, and measurement noise.
          </p>
        </div>
        <Button variant="primary" size="sm" type="button" onClick={handleAddSensor} style={{ padding: '2px 8px', fontSize: '11px' }}>
          + Add Sensor
        </Button>
      </div>

      {sensors.length === 0 ? (
        <div style={{ padding: '16px', textAlign: 'center', backgroundColor: 'var(--bg-canvas)', borderRadius: 'var(--radius-sm)', border: '1px dashed var(--border-subtle)' }}>
          <p className="text-muted text-xs font-mono" style={{ margin: 0 }}>
            No synthetic sensors configured. Click '+ Add Sensor' to attach simulated detection modalities.
          </p>
        </div>
      ) : (
        sensors.map((sensor, sIdx) => (
          <Card
            key={`sensor-${sIdx}`}
            title={`Sensor #${sIdx + 1}: ${sensor.sensor_id}`}
            badge={
              <span className="font-mono text-xs uppercase-tracking" style={{ color: 'var(--color-accent)' }}>
                {sensor.modality.toUpperCase()}
              </span>
            }
            actions={
              <Button
                variant="ghost"
                size="sm"
                type="button"
                onClick={() => handleRemoveSensor(sIdx)}
                style={{ color: 'var(--status-critical)', padding: '1px 6px', fontSize: '10px' }}
              >
                ✕ Remove Sensor
              </Button>
            }
          >
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {/* Row 1: Identification & Modality */}
              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr 1fr 1fr', gap: '8px' }}>
                <div>
                  <label className="text-muted text-xs uppercase-tracking">Sensor ID *</label>
                  <input
                    type="text"
                    className="tactical-input font-mono"
                    value={sensor.sensor_id}
                    onChange={(e) => handleUpdateSensor(sIdx, { sensor_id: e.target.value.toUpperCase() })}
                    placeholder="SIM-RADAR-01"
                    required
                  />
                </div>

                <div>
                  <label className="text-muted text-xs uppercase-tracking">Modality</label>
                  <select
                    className="tactical-select font-mono"
                    value={sensor.modality}
                    onChange={(e) => handleUpdateSensor(sIdx, { modality: e.target.value.toLowerCase() })}
                  >
                    <option value="radar">RADAR (3D Track Radar)</option>
                    <option value="optical">OPTICAL (EO/IR Camera)</option>
                    <option value="rf">RF (Direction Finder/Scanner)</option>
                  </select>
                </div>

                <div>
                  <label className="text-muted text-xs uppercase-tracking">Range (meters)</label>
                  <input
                    type="number"
                    step="100"
                    min="0"
                    className="tactical-input font-mono"
                    value={sensor.range_meters}
                    onChange={(e) => handleUpdateSensor(sIdx, { range_meters: Math.max(0, parseFloat(e.target.value) || 0) })}
                    required
                  />
                </div>

                <div>
                  <label className="text-muted text-xs uppercase-tracking">Det Probability</label>
                  <input
                    type="number"
                    step="0.05"
                    min="0.0"
                    max="1.0"
                    className="tactical-input font-mono"
                    value={sensor.detection_probability}
                    onChange={(e) => handleUpdateSensor(sIdx, { detection_probability: Math.min(1, Math.max(0, parseFloat(e.target.value) || 0)) })}
                    required
                  />
                </div>
              </div>

              {/* Row 2: Location Position */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
                <div>
                  <label className="text-muted text-xs uppercase-tracking">Latitude (°)</label>
                  <input
                    type="number"
                    step="0.0001"
                    className="tactical-input font-mono"
                    value={sensor.latitude}
                    onChange={(e) => handleUpdateSensor(sIdx, { latitude: parseFloat(e.target.value) || 0 })}
                    required
                  />
                </div>
                <div>
                  <label className="text-muted text-xs uppercase-tracking">Longitude (°)</label>
                  <input
                    type="number"
                    step="0.0001"
                    className="tactical-input font-mono"
                    value={sensor.longitude}
                    onChange={(e) => handleUpdateSensor(sIdx, { longitude: parseFloat(e.target.value) || 0 })}
                    required
                  />
                </div>
                <div>
                  <label className="text-muted text-xs uppercase-tracking">Altitude (m AGL)</label>
                  <input
                    type="number"
                    step="1"
                    min="0"
                    className="tactical-input font-mono"
                    value={sensor.altitude ?? ''}
                    onChange={(e) => handleUpdateSensor(sIdx, { altitude: e.target.value ? parseFloat(e.target.value) : null })}
                    placeholder="10"
                  />
                </div>
              </div>

              {/* Row 3: FOV Gating & Noise */}
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '8px' }}>
                <div>
                  <label className="text-muted text-xs uppercase-tracking">FOV Azimuth Start (°)</label>
                  <input
                    type="number"
                    step="1"
                    min="0"
                    max="359.9"
                    className="tactical-input font-mono"
                    value={sensor.fov_azimuth_start_deg ?? 0}
                    onChange={(e) => handleUpdateSensor(sIdx, { fov_azimuth_start_deg: parseFloat(e.target.value) || 0 })}
                  />
                </div>

                <div>
                  <label className="text-muted text-xs uppercase-tracking">FOV Azimuth Span (°)</label>
                  <input
                    type="number"
                    step="5"
                    min="1"
                    max="360"
                    className="tactical-input font-mono"
                    value={sensor.fov_azimuth_span_deg ?? 360}
                    onChange={(e) => handleUpdateSensor(sIdx, { fov_azimuth_span_deg: Math.min(360, Math.max(1, parseFloat(e.target.value) || 360)) })}
                  />
                </div>

                <div>
                  <label className="text-muted text-xs uppercase-tracking">Position Noise (m)</label>
                  <input
                    type="number"
                    step="0.5"
                    min="0"
                    className="tactical-input font-mono"
                    value={sensor.position_uncertainty_meters}
                    onChange={(e) => handleUpdateSensor(sIdx, { position_uncertainty_meters: Math.max(0, parseFloat(e.target.value) || 0) })}
                    placeholder="5.0"
                  />
                </div>
              </div>
            </div>
          </Card>
        ))
      )}
    </div>
  );
};
