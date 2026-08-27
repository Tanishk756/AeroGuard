import React, { useEffect, useState } from 'react';
import { getSensors } from '../../api/sensors';
import { DETECTION_PRESETS, ingestSyntheticDetection, validateDetectionPayload } from '../../api/developer';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { StatusBadge } from '../common/StatusBadge';
import { useAuth } from '../../context/AuthContext';
import { DetectionIngestionResult, Sensor } from '../../types';

interface DetectionWorkbenchProps {
  initialSensorId?: string;
}

export const DetectionWorkbench: React.FC<DetectionWorkbenchProps> = ({ initialSensorId }) => {
  const { hasPermission } = useAuth();
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [selectedSensorId, setSelectedSensorId] = useState<string>(initialSensorId || '');
  const [customSensorId, setCustomSensorId] = useState<string>('');
  const [selectedPresetId, setSelectedPresetId] = useState<string>(DETECTION_PRESETS[0].id);
  const [sourceDetectionId, setSourceDetectionId] = useState<string>(
    `det-sim-${Date.now().toString().slice(-6)}`
  );
  const [timestamp, setTimestamp] = useState<string>(new Date().toISOString());
  const [latitude, setLatitude] = useState<string>('37.7749');
  const [longitude, setLongitude] = useState<string>('-122.4194');
  const [altitudeM, setAltitudeM] = useState<string>('120.0');
  const [speedMps, setSpeedMps] = useState<string>('18.5');
  const [headingDeg, setHeadingDeg] = useState<string>('45.0');
  const [sourceType, setSourceType] = useState<string>('RADAR');
  const [confidence, setConfidence] = useState<string>('0.92');
  const [metadataJson, setMetadataJson] = useState<string>(
    JSON.stringify({ snr_db: 18.5, rcs_dbsm: -5.0 }, null, 2)
  );

  const [isLoadingSensors, setIsLoadingSensors] = useState<boolean>(false);
  const [isDispatching, setIsDispatching] = useState<boolean>(false);
  const [dispatchResult, setDispatchResult] = useState<DetectionIngestionResult | null>(null);
  const [dispatchError, setDispatchError] = useState<string | null>(null);

  const canConfigure = hasPermission('sensors.configure');

  useEffect(() => {
    const fetchSensorsList = async () => {
      setIsLoadingSensors(true);
      try {
        const res = await getSensors({ limit: 100 });
        setSensors(res.items || []);
        if (res.items && res.items.length > 0 && !selectedSensorId) {
          setSelectedSensorId(res.items[0].id);
        }
      } catch {
        // Sensor list could fail if user lacks sensors.read
      } finally {
        setIsLoadingSensors(false);
      }
    };
    fetchSensorsList();
  }, [selectedSensorId]);

  const handleApplyPreset = (presetId: string) => {
    setSelectedPresetId(presetId);
    const preset = DETECTION_PRESETS.find((p) => p.id === presetId);
    if (!preset) return;

    setSourceDetectionId(`det-${preset.source_type.toLowerCase()}-${Date.now().toString().slice(-6)}`);
    setTimestamp(new Date().toISOString());
    setLatitude(String(preset.payload.latitude));
    setLongitude(String(preset.payload.longitude));
    setAltitudeM(String(preset.payload.altitude_m));
    setSpeedMps(preset.payload.speed_mps !== undefined ? String(preset.payload.speed_mps) : '');
    setHeadingDeg(preset.payload.heading_deg !== undefined ? String(preset.payload.heading_deg) : '');
    setSourceType(preset.payload.source_type);
    setConfidence(String(preset.payload.confidence));
    setMetadataJson(JSON.stringify(preset.payload.metadata, null, 2));
    setDispatchResult(null);
    setDispatchError(null);
  };

  const handleSetNow = () => {
    setTimestamp(new Date().toISOString());
  };

  const handleRandomizeId = () => {
    setSourceDetectionId(`det-${sourceType.toLowerCase()}-${Date.now().toString().slice(-6)}`);
  };

  // Build payload object for live validation
  let parsedMetadata: Record<string, unknown> = {};
  let metadataError: string | null = null;
  try {
    if (metadataJson.trim()) {
      parsedMetadata = JSON.parse(metadataJson);
    }
  } catch {
    metadataError = 'Metadata must be valid JSON';
  }

  const payloadToValidate: Record<string, unknown> = {
    source_detection_id: sourceDetectionId,
    timestamp,
    latitude: parseFloat(latitude),
    longitude: parseFloat(longitude),
    altitude_m: parseFloat(altitudeM),
    speed_mps: speedMps.trim() ? parseFloat(speedMps) : undefined,
    heading_deg: headingDeg.trim() ? parseFloat(headingDeg) : undefined,
    source_type: sourceType,
    confidence: parseFloat(confidence),
    metadata: parsedMetadata,
  };

  const validation = validateDetectionPayload(payloadToValidate);
  const targetSensorId = selectedSensorId || customSensorId;

  const handleDispatch = async () => {
    if (!validation.valid || !targetSensorId.trim() || metadataError) {
      return;
    }

    setIsDispatching(true);
    setDispatchError(null);
    setDispatchResult(null);

    try {
      const result = await ingestSyntheticDetection(targetSensorId, payloadToValidate);
      setDispatchResult(result);
    } catch (err: unknown) {
      setDispatchError(err instanceof Error ? err.message : 'Ingestion failed');
    } finally {
      setIsDispatching(false);
    }
  };

  return (
    <div style={{ display: 'grid', gridTemplateColumns: 'minmax(340px, 1.2fr) minmax(320px, 0.8fr)', gap: 'var(--space-md)' }}>
      {/* Left Column: Form & Presets */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
        <Card title="Synthetic Detection Ingestion Workbench">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
            {/* Target Sensor Selection */}
            <div>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'baseline', marginBottom: '4px' }}>
                <label className="uppercase-tracking text-muted" style={{ fontSize: '10px' }}>
                  Target Sensor System <span style={{ color: 'var(--status-critical)' }}>*</span>
                </label>
                <span className="font-mono text-xs text-muted">
                  {isLoadingSensors ? 'Loading sensors...' : `${sensors.length} sensors registered`}
                </span>
              </div>

              {sensors.length > 0 ? (
                <select
                  className="tactical-input"
                  value={selectedSensorId}
                  onChange={(e) => setSelectedSensorId(e.target.value)}
                  style={{ width: '100%' }}
                >
                  {sensors.map((s) => (
                    <option key={s.id} value={s.id}>
                      {s.name} ({s.source_type} • {s.status}) — Lat: {s.configuration_metadata?.latitude?.toFixed(3) ?? 'N/A'}, Lon: {s.configuration_metadata?.longitude?.toFixed(3) ?? 'N/A'}, Range: {s.configuration_metadata?.range_meters || 'N/A'}m
                    </option>
                  ))}
                </select>
              ) : (
                <input
                  type="text"
                  className="tactical-input font-mono"
                  value={customSensorId}
                  onChange={(e) => setCustomSensorId(e.target.value)}
                  placeholder="Enter Target Sensor UUID..."
                  style={{ width: '100%' }}
                />
              )}
            </div>

            {/* Presets Toolbar */}
            <div>
              <span className="uppercase-tracking text-muted" style={{ fontSize: '10px', display: 'block', marginBottom: '6px' }}>
                Observation Modality Presets
              </span>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '6px' }}>
                {DETECTION_PRESETS.map((preset) => {
                  const isSelected = selectedPresetId === preset.id;
                  return (
                    <button
                      key={preset.id}
                      type="button"
                      onClick={() => handleApplyPreset(preset.id)}
                      className="tactical-btn"
                      style={{
                        padding: '6px 8px',
                        display: 'flex',
                        flexDirection: 'column',
                        alignItems: 'flex-start',
                        gap: '2px',
                        backgroundColor: isSelected ? 'var(--bg-surface-active)' : 'var(--bg-canvas)',
                        borderLeft: isSelected ? '3px solid var(--color-accent)' : '3px solid transparent',
                        textAlign: 'left',
                      }}
                    >
                      <span className="font-mono" style={{ fontSize: '11px', fontWeight: 600, color: isSelected ? 'var(--color-accent)' : 'var(--text-primary)' }}>
                        {preset.source_type}
                      </span>
                      <span style={{ fontSize: '10px', color: 'var(--text-muted)' }}>
                        {preset.name}
                      </span>
                    </button>
                  );
                })}
              </div>
            </div>

            {/* Ingestion Parameters Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-sm)' }}>
              {/* Source Detection ID */}
              <div style={{ gridColumn: '1 / -1' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
                  <label className="uppercase-tracking text-muted" style={{ fontSize: '10px' }}>
                    Source Detection ID
                  </label>
                  <button type="button" onClick={handleRandomizeId} className="tactical-btn" style={{ padding: '1px 6px', fontSize: '10px' }}>
                    Regenerate ID
                  </button>
                </div>
                <input
                  type="text"
                  className="tactical-input font-mono"
                  value={sourceDetectionId}
                  onChange={(e) => setSourceDetectionId(e.target.value)}
                />
              </div>

              {/* Timestamp */}
              <div style={{ gridColumn: '1 / -1' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2px' }}>
                  <label className="uppercase-tracking text-muted" style={{ fontSize: '10px' }}>
                    Observation Timestamp (UTC)
                  </label>
                  <button type="button" onClick={handleSetNow} className="tactical-btn" style={{ padding: '1px 6px', fontSize: '10px' }}>
                    Set to Now
                  </button>
                </div>
                <input
                  type="text"
                  className="tactical-input font-mono"
                  value={timestamp}
                  onChange={(e) => setTimestamp(e.target.value)}
                />
              </div>

              {/* Latitude */}
              <div>
                <label className="uppercase-tracking text-muted" style={{ fontSize: '10px', display: 'block', marginBottom: '2px' }}>
                  Latitude [-90.0, 90.0]
                </label>
                <input
                  type="number"
                  step="0.0001"
                  className="tactical-input font-mono"
                  value={latitude}
                  onChange={(e) => setLatitude(e.target.value)}
                />
              </div>

              {/* Longitude */}
              <div>
                <label className="uppercase-tracking text-muted" style={{ fontSize: '10px', display: 'block', marginBottom: '2px' }}>
                  Longitude [-180.0, 180.0]
                </label>
                <input
                  type="number"
                  step="0.0001"
                  className="tactical-input font-mono"
                  value={longitude}
                  onChange={(e) => setLongitude(e.target.value)}
                />
              </div>

              {/* Altitude */}
              <div>
                <label className="uppercase-tracking text-muted" style={{ fontSize: '10px', display: 'block', marginBottom: '2px' }}>
                  Altitude AGL (meters) [&gt;= 0]
                </label>
                <input
                  type="number"
                  step="0.1"
                  className="tactical-input font-mono"
                  value={altitudeM}
                  onChange={(e) => setAltitudeM(e.target.value)}
                />
              </div>

              {/* Speed */}
              <div>
                <label className="uppercase-tracking text-muted" style={{ fontSize: '10px', display: 'block', marginBottom: '2px' }}>
                  Ground Speed (m/s) [&gt;= 0]
                </label>
                <input
                  type="number"
                  step="0.1"
                  className="tactical-input font-mono"
                  value={speedMps}
                  onChange={(e) => setSpeedMps(e.target.value)}
                />
              </div>

              {/* Heading */}
              <div>
                <label className="uppercase-tracking text-muted" style={{ fontSize: '10px', display: 'block', marginBottom: '2px' }}>
                  Heading [0.0, 360.0)°
                </label>
                <input
                  type="number"
                  step="1"
                  className="tactical-input font-mono"
                  value={headingDeg}
                  onChange={(e) => setHeadingDeg(e.target.value)}
                />
              </div>

              {/* Confidence */}
              <div>
                <label className="uppercase-tracking text-muted" style={{ fontSize: '10px', display: 'block', marginBottom: '2px' }}>
                  Confidence [0.0, 1.0]
                </label>
                <input
                  type="number"
                  step="0.01"
                  className="tactical-input font-mono"
                  value={confidence}
                  onChange={(e) => setConfidence(e.target.value)}
                />
              </div>

              {/* Source Type */}
              <div style={{ gridColumn: '1 / -1' }}>
                <label className="uppercase-tracking text-muted" style={{ fontSize: '10px', display: 'block', marginBottom: '2px' }}>
                  Modality Classification
                </label>
                <select
                  className="tactical-input"
                  value={sourceType}
                  onChange={(e) => setSourceType(e.target.value)}
                  style={{ width: '100%' }}
                >
                  <option value="RADAR">RADAR — Radio Detection & Ranging</option>
                  <option value="RF">RF — Radio Frequency Spectrum Emission</option>
                  <option value="OPTICAL">OPTICAL — EO/IR Visual Camera Sensor</option>
                  <option value="ACOUSTIC">ACOUSTIC — Acoustic Sensor Array</option>
                </select>
              </div>

              {/* Metadata JSON */}
              <div style={{ gridColumn: '1 / -1' }}>
                <label className="uppercase-tracking text-muted" style={{ fontSize: '10px', display: 'block', marginBottom: '2px' }}>
                  Modality Metadata (JSON)
                </label>
                <textarea
                  className="tactical-input font-mono"
                  value={metadataJson}
                  onChange={(e) => setMetadataJson(e.target.value)}
                  rows={4}
                  style={{ width: '100%', fontSize: '11px', lineHeight: 1.4 }}
                />
                {metadataError && (
                  <span style={{ fontSize: '11px', color: 'var(--status-critical)' }}>{metadataError}</span>
                )}
              </div>
            </div>

            {/* Ingestion Submit Action */}
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', borderTop: '1px solid var(--border-subtle)', paddingTop: 'var(--space-sm)' }}>
              <div>
                {!canConfigure && (
                  <span style={{ color: 'var(--status-critical)', fontSize: '11px' }}>
                    Requires <code className="font-mono">sensors.configure</code> authority.
                  </span>
                )}
              </div>
              <Button
                variant="primary"
                onClick={handleDispatch}
                isLoading={isDispatching}
                disabled={!canConfigure || !validation.valid || Boolean(metadataError)}
              >
                Inject Detection Observation 🚀
              </Button>
            </div>
          </div>
        </Card>
      </div>

      {/* Right Column: Validation & Dispatch Results */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
        {/* Realtime Coordinate & Field Validation Card */}
        <Card title="Kinematic & Schema Validation">
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <span className="uppercase-tracking text-muted" style={{ fontSize: '10px' }}>
                Payload Mathematical Sanity
              </span>
              <StatusBadge
                status={validation.valid && !metadataError ? 'ACTIVE' : 'CRITICAL'}
                label={validation.valid && !metadataError ? 'VALID' : 'INVALID'}
              />
            </div>

            {validation.errors.length > 0 || metadataError ? (
              <div
                style={{
                  padding: '10px',
                  backgroundColor: 'rgba(239, 68, 68, 0.1)',
                  border: '1px solid rgba(239, 68, 68, 0.3)',
                  borderRadius: 'var(--radius-sm)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '4px',
                }}
              >
                {validation.errors.map((err, idx) => (
                  <div key={idx} style={{ fontSize: '11px', color: 'var(--status-critical)' }}>
                    • {err}
                  </div>
                ))}
                {metadataError && (
                  <div style={{ fontSize: '11px', color: 'var(--status-critical)' }}>
                    • {metadataError}
                  </div>
                )}
              </div>
            ) : (
              <div
                style={{
                  padding: '10px',
                  backgroundColor: 'rgba(16, 185, 129, 0.1)',
                  border: '1px solid rgba(16, 185, 129, 0.3)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '11px',
                  color: 'var(--status-active)',
                }}
              >
                ✓ All kinematic bounds, coordinate ranges, and timestamps conform to backend Stage F2/F3 ingestion standards.
              </div>
            )}

            <div className="font-mono text-xs text-muted" style={{ marginTop: '8px' }}>
              <div>• Latitude: {latitude}° ([-90.0, 90.0])</div>
              <div>• Longitude: {longitude}° ([-180.0, 180.0])</div>
              <div>• Altitude: {altitudeM} m (&gt;= 0.0)</div>
              <div>• Speed: {speedMps || '0'} m/s (&gt;= 0.0)</div>
              <div>• Heading: {headingDeg || '0'}° ([0.0, 360.0))</div>
              <div>• Confidence: {confidence} ([0.0, 1.0])</div>
            </div>
          </div>
        </Card>

        {/* Dispatch Result Card */}
        <Card title="Ingestion Engine Result">
          {dispatchResult ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                <span className="font-mono text-xs" style={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                  HTTP 201 / 200 SUCCESS
                </span>
                <StatusBadge
                  status={dispatchResult.created ? 'ACTIVE' : 'WARNING'}
                  label={dispatchResult.created ? 'NEW OBSERVATION' : 'IDEMPOTENT DUPLICATE'}
                />
              </div>

              <div
                style={{
                  padding: '10px',
                  backgroundColor: 'var(--bg-canvas)',
                  borderRadius: 'var(--radius-sm)',
                  border: '1px solid var(--border-subtle)',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '6px',
                }}
              >
                <div className="kv-row">
                  <span className="kv-key">Detection ID</span>
                  <span className="kv-value font-mono text-xs" style={{ color: 'var(--color-accent)' }}>
                    {dispatchResult.detection_id}
                  </span>
                </div>
                <div className="kv-row">
                  <span className="kv-key">Created</span>
                  <span className="kv-value font-mono text-xs">
                    {dispatchResult.created ? 'true (New Record)' : 'false (Duplicate Deduplicated)'}
                  </span>
                </div>
                <div className="kv-row">
                  <span className="kv-key">Sensor ID</span>
                  <span className="kv-value font-mono text-xs text-muted">
                    {dispatchResult.sensor_id}
                  </span>
                </div>
                <div className="kv-row">
                  <span className="kv-key">Source Det ID</span>
                  <span className="kv-value font-mono text-xs">
                    {dispatchResult.source_detection_id}
                  </span>
                </div>
                <div className="kv-row">
                  <span className="kv-key">Ingested Time</span>
                  <span className="kv-value font-mono text-xs text-muted">
                    {dispatchResult.timestamp}
                  </span>
                </div>
              </div>

              <div
                style={{
                  padding: '8px 10px',
                  backgroundColor: 'rgba(56, 189, 248, 0.1)',
                  borderRadius: 'var(--radius-sm)',
                  fontSize: '11px',
                  color: 'var(--text-secondary)',
                }}
              >
                💡 Observation has been passed to Stage F3 track correlation. Visit <strong>Tracks</strong> to inspect track progression.
              </div>
            </div>
          ) : dispatchError ? (
            <div
              style={{
                padding: '12px',
                backgroundColor: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--status-critical)',
                fontSize: '12px',
              }}
            >
              <strong>Ingestion Rejected:</strong> {dispatchError}
            </div>
          ) : (
            <div style={{ padding: 'var(--space-lg)', textAlign: 'center', color: 'var(--text-muted)', fontSize: '11px' }}>
              No detection injected yet. Configure parameters and click "Inject Detection Observation".
            </div>
          )}
        </Card>
      </div>
    </div>
  );
};
