import React, { useEffect, useMemo, useState } from 'react';
import { Geofence, GeofenceCreate, GeofenceGeometry, GeofenceUpdate } from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';

interface GeofenceEditorProps {
  isOpen: boolean;
  initialGeofence?: Geofence | null;
  onClose: () => void;
  onSave: (data: GeofenceCreate | GeofenceUpdate) => Promise<void>;
  onDraftGeometryChange?: (geometry: GeofenceGeometry | null) => void;
}

interface PolygonVertexRow {
  id: string;
  lat: string;
  lon: string;
}

export const GeofenceEditor: React.FC<GeofenceEditorProps> = ({
  isOpen,
  initialGeofence,
  onClose,
  onSave,
  onDraftGeometryChange,
}) => {
  const isEditing = !!initialGeofence;

  // Form fields
  const [name, setName] = useState<string>('');
  const [enabled, setEnabled] = useState<boolean>(true);
  const [ruleType, setRuleType] = useState<'INCLUSION' | 'EXCLUSION'>('EXCLUSION');
  const [geometryType, setGeometryType] = useState<'bbox' | 'polygon'>('bbox');

  // BBox fields
  const [minLat, setMinLat] = useState<string>('37.7500');
  const [minLon, setMinLon] = useState<string>('-122.4500');
  const [maxLat, setMaxLat] = useState<string>('37.8000');
  const [maxLon, setMaxLon] = useState<string>('-122.4000');

  // Polygon fields
  const [vertices, setVertices] = useState<PolygonVertexRow[]>([
    { id: 'v1', lat: '37.7749', lon: '-122.4194' },
    { id: 'v2', lat: '37.7849', lon: '-122.4094' },
    { id: 'v3', lat: '37.7649', lon: '-122.3994' },
  ]);
  const [pasteMode, setPasteMode] = useState<boolean>(false);
  const [pasteText, setPasteText] = useState<string>('');

  // Altitude fields
  const [minAltitude, setMinAltitude] = useState<string>('');
  const [maxAltitude, setMaxAltitude] = useState<string>('');

  // Safety & State management
  const [isDirty, setIsDirty] = useState<boolean>(false);
  const [showUnsavedWarning, setShowUnsavedWarning] = useState<boolean>(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Initialize form when opened
  useEffect(() => {
    if (isOpen) {
      if (initialGeofence) {
        setName(initialGeofence.name);
        setEnabled(initialGeofence.enabled);
        setRuleType((initialGeofence.metadata?.rule as 'INCLUSION' | 'EXCLUSION') || 'EXCLUSION');
        setMinAltitude(initialGeofence.min_altitude != null ? String(initialGeofence.min_altitude) : '');
        setMaxAltitude(initialGeofence.max_altitude != null ? String(initialGeofence.max_altitude) : '');

        if (initialGeofence.geometry.type === 'bbox') {
          setGeometryType('bbox');
          setMinLat(String(initialGeofence.geometry.min_lat));
          setMinLon(String(initialGeofence.geometry.min_lon));
          setMaxLat(String(initialGeofence.geometry.max_lat));
          setMaxLon(String(initialGeofence.geometry.max_lon));
        } else if (initialGeofence.geometry.type === 'polygon') {
          setGeometryType('polygon');
          setVertices(
            initialGeofence.geometry.coordinates.map((pt, idx) => ({
              id: `v-${idx}-${Date.now()}`,
              lat: String(pt[0]),
              lon: String(pt[1]),
            }))
          );
        }
      } else {
        // Reset defaults for new zone
        setName('');
        setEnabled(true);
        setRuleType('EXCLUSION');
        setGeometryType('bbox');
        setMinLat('37.7500');
        setMinLon('-122.4500');
        setMaxLat('37.8000');
        setMaxLon('-122.4000');
        setVertices([
          { id: 'v1', lat: '37.7749', lon: '-122.4194' },
          { id: 'v2', lat: '37.7849', lon: '-122.4094' },
          { id: 'v3', lat: '37.7649', lon: '-122.3994' },
        ]);
        setMinAltitude('');
        setMaxAltitude('');
      }
      setIsDirty(false);
      setShowUnsavedWarning(false);
      setValidationError(null);
      setPasteMode(false);
      setPasteText('');
    }
  }, [isOpen, initialGeofence]);

  // Compute current draft geometry for TacticalMap live preview
  const currentDraftGeometry: GeofenceGeometry | null = useMemo(() => {
    if (geometryType === 'bbox') {
      const nMinLat = parseFloat(minLat);
      const nMinLon = parseFloat(minLon);
      const nMaxLat = parseFloat(maxLat);
      const nMaxLon = parseFloat(maxLon);
      if (
        !isNaN(nMinLat) &&
        !isNaN(nMinLon) &&
        !isNaN(nMaxLat) &&
        !isNaN(nMaxLon) &&
        nMinLat <= nMaxLat &&
        nMinLon <= nMaxLon
      ) {
        return {
          type: 'bbox',
          min_lat: nMinLat,
          min_lon: nMinLon,
          max_lat: nMaxLat,
          max_lon: nMaxLon,
        };
      }
    } else if (geometryType === 'polygon') {
      const validCoords: [number, number][] = [];
      for (const v of vertices) {
        const lat = parseFloat(v.lat);
        const lon = parseFloat(v.lon);
        if (!isNaN(lat) && !isNaN(lon)) {
          validCoords.push([lat, lon]);
        }
      }
      if (validCoords.length >= 3) {
        return {
          type: 'polygon',
          coordinates: validCoords,
        };
      }
    }
    return null;
  }, [geometryType, minLat, minLon, maxLat, maxLon, vertices]);

  // Notify map when draft geometry changes
  useEffect(() => {
    if (isOpen) {
      onDraftGeometryChange?.(currentDraftGeometry);
    } else {
      onDraftGeometryChange?.(null);
    }
  }, [isOpen, currentDraftGeometry, onDraftGeometryChange]);

  const markDirty = () => setIsDirty(true);

  // Polygon vertex manipulation
  const handleAddVertex = () => {
    setVertices((prev) => [
      ...prev,
      { id: `v-${Date.now()}-${prev.length + 1}`, lat: '37.7700', lon: '-122.4100' },
    ]);
    markDirty();
  };

  const handleUpdateVertex = (id: string, field: 'lat' | 'lon', value: string) => {
    setVertices((prev) =>
      prev.map((v) => (v.id === id ? { ...v, [field]: value } : v))
    );
    markDirty();
  };

  const handleDeleteVertex = (id: string) => {
    if (vertices.length <= 3) {
      setValidationError('Polygons require at least 3 vertices.');
      return;
    }
    setVertices((prev) => prev.filter((v) => v.id !== id));
    markDirty();
  };

  const handleApplyPasteCoordinates = () => {
    setValidationError(null);
    try {
      // Parse JSON array of [lat, lon] pairs
      const parsed = JSON.parse(pasteText.trim());
      if (!Array.isArray(parsed) || parsed.length < 3) {
        throw new Error('Pasted coordinate data must be an array of at least 3 [latitude, longitude] pairs.');
      }
      const newVertices: PolygonVertexRow[] = [];
      for (let i = 0; i < parsed.length; i++) {
        const pt = parsed[i];
        if (!Array.isArray(pt) || pt.length !== 2 || typeof pt[0] !== 'number' || typeof pt[1] !== 'number') {
          throw new Error(`Invalid coordinate pair at index ${i}: ${JSON.stringify(pt)}`);
        }
        if (pt[0] < -90 || pt[0] > 90 || pt[1] < -180 || pt[1] > 180) {
          throw new Error(`Coordinates at index ${i} out of valid GPS range [-90..90, -180..180].`);
        }
        newVertices.push({
          id: `v-${i}-${Date.now()}`,
          lat: String(pt[0]),
          lon: String(pt[1]),
        });
      }
      setVertices(newVertices);
      setPasteMode(false);
      setPasteText('');
      markDirty();
    } catch (err: unknown) {
      setValidationError(err instanceof Error ? err.message : 'Failed to parse pasted coordinate array.');
    }
  };

  // Safe close handler with unsaved changes detection
  const handleRequestClose = () => {
    if (isDirty) {
      setShowUnsavedWarning(true);
    } else {
      onClose();
    }
  };

  const handleConfirmDiscard = () => {
    setShowUnsavedWarning(false);
    setIsDirty(false);
    onClose();
  };

  // Submit & Validation
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    // 1. Validate name
    const trimmedName = name.trim();
    if (!trimmedName) {
      setValidationError('Zone name is required.');
      return;
    }

    // 2. Validate geometry
    let geometryPayload: GeofenceGeometry;
    if (geometryType === 'bbox') {
      const nMinLat = parseFloat(minLat);
      const nMinLon = parseFloat(minLon);
      const nMaxLat = parseFloat(maxLat);
      const nMaxLon = parseFloat(maxLon);

      if (isNaN(nMinLat) || isNaN(nMinLon) || isNaN(nMaxLat) || isNaN(nMaxLon)) {
        setValidationError('All four bounding box coordinate bounds must be valid numbers.');
        return;
      }
      if (nMinLat < -90 || nMaxLat > 90 || nMinLon < -180 || nMaxLon > 180) {
        setValidationError('Bounding box coordinates must be within standard GPS ranges (-90 to 90 lat, -180 to 180 lon).');
        return;
      }
      if (nMinLat >= nMaxLat) {
        setValidationError('Minimum latitude must be strictly less than maximum latitude.');
        return;
      }
      if (nMinLon >= nMaxLon) {
        setValidationError('Minimum longitude must be strictly less than maximum longitude.');
        return;
      }
      geometryPayload = {
        type: 'bbox',
        min_lat: nMinLat,
        min_lon: nMinLon,
        max_lat: nMaxLat,
        max_lon: nMaxLon,
      };
    } else {
      if (vertices.length < 3) {
        setValidationError('Polygons must contain at least 3 vertices.');
        return;
      }
      const coords: [number, number][] = [];
      for (let i = 0; i < vertices.length; i++) {
        const lat = parseFloat(vertices[i].lat);
        const lon = parseFloat(vertices[i].lon);
        if (isNaN(lat) || isNaN(lon)) {
          setValidationError(`Vertex #${i + 1} has invalid latitude or longitude.`);
          return;
        }
        if (lat < -90 || lat > 90 || lon < -180 || lon > 180) {
          setValidationError(`Vertex #${i + 1} coordinates out of GPS range [-90..90, -180..180].`);
          return;
        }
        coords.push([lat, lon]);
      }
      geometryPayload = {
        type: 'polygon',
        coordinates: coords,
      };
    }

    // 3. Validate altitude constraints
    const nMinAlt = minAltitude.trim() ? parseFloat(minAltitude) : undefined;
    const nMaxAlt = maxAltitude.trim() ? parseFloat(maxAltitude) : undefined;

    if (nMinAlt !== undefined && (isNaN(nMinAlt) || nMinAlt < 0)) {
      setValidationError('Minimum altitude must be a non-negative number.');
      return;
    }
    if (nMaxAlt !== undefined && (isNaN(nMaxAlt) || nMaxAlt < 0)) {
      setValidationError('Maximum altitude must be a non-negative number.');
      return;
    }
    if (nMinAlt !== undefined && nMaxAlt !== undefined && nMinAlt > nMaxAlt) {
      setValidationError('Minimum altitude cannot exceed maximum altitude.');
      return;
    }

    // Construct request payload
    const payload: GeofenceCreate | GeofenceUpdate = {
      name: trimmedName,
      enabled,
      geometry: geometryPayload,
      min_altitude: nMinAlt ?? null,
      max_altitude: nMaxAlt ?? null,
      metadata: {
        rule: ruleType,
        authored_via: 'operator_console',
      },
    };

    setIsSubmitting(true);
    try {
      await onSave(payload);
      setIsDirty(false);
      onClose();
    } catch (err: unknown) {
      setValidationError(err instanceof Error ? err.message : 'Failed to save geofence configuration.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="geofence-editor-title"
      style={{
        position: 'fixed',
        inset: 0,
        backgroundColor: 'rgba(2, 6, 12, 0.75)',
        backdropFilter: 'blur(2px)',
        zIndex: 9990,
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--space-md)',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: '680px',
          maxHeight: '90vh',
          backgroundColor: 'var(--bg-surface-elevated)',
          border: '1px solid var(--border-medium)',
          borderRadius: 'var(--radius-md)',
          boxShadow: 'var(--shadow-lg)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <div
          style={{
            padding: '12px 16px',
            borderBottom: '1px solid var(--border-medium)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            backgroundColor: 'var(--bg-surface)',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', backgroundColor: 'var(--status-warning)', borderRadius: '1px' }} />
            <h2 id="geofence-editor-title" className="font-mono text-sm" style={{ fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
              {isEditing ? `EDIT DEFENSE ZONE: ${initialGeofence?.name}` : 'CREATE DEFENSE ZONE (GEOFENCE)'}
            </h2>
          </div>
          <Button variant="ghost" size="sm" onClick={handleRequestClose} style={{ padding: '2px 6px', fontSize: '11px' }}>
            ✕
          </Button>
        </div>

        {/* Scrollable Form Content */}
        <form onSubmit={handleSubmit} style={{ overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          {validationError && (
            <div
              style={{
                padding: '8px 12px',
                backgroundColor: 'var(--status-critical-bg)',
                border: '1px solid var(--status-critical-border)',
                borderRadius: 'var(--radius-sm)',
                color: 'var(--status-critical)',
                fontSize: '11px',
                fontFamily: 'monospace',
              }}
            >
              ⚠ {validationError}
            </div>
          )}

          {/* Section 1: General Identity & Rule */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr 1fr', gap: '10px' }}>
            <div>
              <label className="text-muted text-xs uppercase-tracking" style={{ display: 'block', marginBottom: '2px' }}>
                Zone Identifier / Name *
              </label>
              <input
                type="text"
                className="tactical-input font-mono"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  markDirty();
                }}
                placeholder="e.g. NORTH_PERIMETER_RESTRICTED"
                required
              />
            </div>

            <div>
              <label className="text-muted text-xs uppercase-tracking" style={{ display: 'block', marginBottom: '2px' }}>
                Zone Rule Type
              </label>
              <select
                className="tactical-select font-mono"
                value={ruleType}
                onChange={(e) => {
                  setRuleType(e.target.value as 'INCLUSION' | 'EXCLUSION');
                  markDirty();
                }}
              >
                <option value="EXCLUSION">EXCLUSION (Keep-Out)</option>
                <option value="INCLUSION">INCLUSION (Allowed Zone)</option>
              </select>
            </div>

            <div>
              <label className="text-muted text-xs uppercase-tracking" style={{ display: 'block', marginBottom: '2px' }}>
                Operational Status
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '6px', height: '32px', fontSize: '11px' }}>
                <input
                  type="checkbox"
                  checked={enabled}
                  onChange={(e) => {
                    setEnabled(e.target.checked);
                    markDirty();
                  }}
                />
                <span className="font-mono">{enabled ? 'Active / Enabled' : 'Disabled'}</span>
              </label>
            </div>
          </div>

          {/* Section 2: Geometry Type Selection */}
          <Card title="Zone Geometry Boundary Configuration">
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              <div style={{ display: 'flex', gap: '12px', borderBottom: '1px solid var(--border-subtle)', paddingBottom: '8px' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', cursor: 'pointer' }}>
                  <input
                    type="radio"
                    name="geomType"
                    checked={geometryType === 'bbox'}
                    onChange={() => {
                      setGeometryType('bbox');
                      markDirty();
                    }}
                  />
                  <span className="font-mono">2D Bounding Box (Min/Max Rect)</span>
                </label>
                <label style={{ display: 'flex', alignItems: 'center', gap: '4px', fontSize: '11px', cursor: 'pointer' }}>
                  <input
                    type="radio"
                    name="geomType"
                    checked={geometryType === 'polygon'}
                    onChange={() => {
                      setGeometryType('polygon');
                      markDirty();
                    }}
                  />
                  <span className="font-mono">Multi-Vertex Polygon (Custom Perimeter)</span>
                </label>
              </div>

              {/* BBox Mode Controls */}
              {geometryType === 'bbox' ? (
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '8px' }}>
                  <div>
                    <label className="text-muted text-xs uppercase-tracking">Min Latitude (South)</label>
                    <input
                      type="number"
                      step="0.0001"
                      className="tactical-input font-mono"
                      value={minLat}
                      onChange={(e) => {
                        setMinLat(e.target.value);
                        markDirty();
                      }}
                      required
                    />
                  </div>
                  <div>
                    <label className="text-muted text-xs uppercase-tracking">Max Latitude (North)</label>
                    <input
                      type="number"
                      step="0.0001"
                      className="tactical-input font-mono"
                      value={maxLat}
                      onChange={(e) => {
                        setMaxLat(e.target.value);
                        markDirty();
                      }}
                      required
                    />
                  </div>
                  <div>
                    <label className="text-muted text-xs uppercase-tracking">Min Longitude (West)</label>
                    <input
                      type="number"
                      step="0.0001"
                      className="tactical-input font-mono"
                      value={minLon}
                      onChange={(e) => {
                        setMinLon(e.target.value);
                        markDirty();
                      }}
                      required
                    />
                  </div>
                  <div>
                    <label className="text-muted text-xs uppercase-tracking">Max Longitude (East)</label>
                    <input
                      type="number"
                      step="0.0001"
                      className="tactical-input font-mono"
                      value={maxLon}
                      onChange={(e) => {
                        setMaxLon(e.target.value);
                        markDirty();
                      }}
                      required
                    />
                  </div>
                </div>
              ) : (
                /* Polygon Mode Controls */
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span className="text-muted text-xs uppercase-tracking">
                      Polygon Vertex Sequence ({vertices.length} points)
                    </span>
                    <div style={{ display: 'flex', gap: '4px' }}>
                      <Button
                        variant="secondary"
                        size="sm"
                        type="button"
                        onClick={() => setPasteMode((prev) => !prev)}
                        style={{ padding: '2px 6px', fontSize: '10px' }}
                      >
                        {pasteMode ? 'Cancel Paste' : '📋 Paste Raw Coordinates'}
                      </Button>
                      <Button
                        variant="primary"
                        size="sm"
                        type="button"
                        onClick={handleAddVertex}
                        style={{ padding: '2px 6px', fontSize: '10px' }}
                      >
                        + Add Vertex
                      </Button>
                    </div>
                  </div>

                  {pasteMode ? (
                    <div style={{ display: 'flex', flexDirection: 'column', gap: '6px', backgroundColor: 'var(--bg-canvas)', padding: '8px', borderRadius: 'var(--radius-sm)' }}>
                      <label className="text-muted text-xs">Paste JSON Coordinate Array `[[lat, lon], [lat, lon], ...]`: </label>
                      <textarea
                        className="tactical-input font-mono"
                        rows={3}
                        value={pasteText}
                        onChange={(e) => setPasteText(e.target.value)}
                        placeholder="[[37.7749, -122.4194], [37.7849, -122.4094], [37.7649, -122.3994]]"
                      />
                      <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '4px' }}>
                        <Button variant="ghost" size="sm" type="button" onClick={() => setPasteMode(false)}>Cancel</Button>
                        <Button variant="primary" size="sm" type="button" onClick={handleApplyPasteCoordinates}>Apply Coordinates</Button>
                      </div>
                    </div>
                  ) : (
                    <div style={{ maxHeight: '180px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '4px' }}>
                      {vertices.map((v, idx) => (
                        <div
                          key={v.id}
                          style={{
                            display: 'grid',
                            gridTemplateColumns: '32px 1fr 1fr 28px',
                            gap: '6px',
                            alignItems: 'center',
                            backgroundColor: 'var(--bg-canvas)',
                            padding: '4px 6px',
                            borderRadius: 'var(--radius-sm)',
                          }}
                        >
                          <span className="font-mono text-xs text-muted">#{idx + 1}</span>
                          <input
                            type="number"
                            step="0.0001"
                            className="tactical-input font-mono"
                            value={v.lat}
                            onChange={(e) => handleUpdateVertex(v.id, 'lat', e.target.value)}
                            placeholder="Latitude"
                            required
                          />
                          <input
                            type="number"
                            step="0.0001"
                            className="tactical-input font-mono"
                            value={v.lon}
                            onChange={(e) => handleUpdateVertex(v.id, 'lon', e.target.value)}
                            placeholder="Longitude"
                            required
                          />
                          <Button
                            variant="ghost"
                            size="sm"
                            type="button"
                            onClick={() => handleDeleteVertex(v.id)}
                            disabled={vertices.length <= 3}
                            style={{ padding: '0', height: '24px', color: 'var(--status-critical)' }}
                            title="Delete Vertex"
                          >
                            ✕
                          </Button>
                        </div>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          </Card>

          {/* Section 3: Altitude Constraints */}
          <Card title="Vertical Airspace Boundaries (Altitude Limits)">
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              <div>
                <label className="text-muted text-xs uppercase-tracking">Floor: Min Altitude (m AGL)</label>
                <input
                  type="number"
                  step="1"
                  min="0"
                  className="tactical-input font-mono"
                  value={minAltitude}
                  onChange={(e) => {
                    setMinAltitude(e.target.value);
                    markDirty();
                  }}
                  placeholder="0 (Ground Level / Surface)"
                />
              </div>
              <div>
                <label className="text-muted text-xs uppercase-tracking">Ceiling: Max Altitude (m AGL)</label>
                <input
                  type="number"
                  step="1"
                  min="0"
                  className="tactical-input font-mono"
                  value={maxAltitude}
                  onChange={(e) => {
                    setMaxAltitude(e.target.value);
                    markDirty();
                  }}
                  placeholder="e.g. 500 (No ceiling if empty)"
                />
              </div>
            </div>
          </Card>

          {/* Footer Actions */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: '6px' }}>
            <span className="font-mono text-xs text-muted">
              {currentDraftGeometry ? '✓ Boundary verified and rendered on TacticalMap' : '⚠ Incomplete geometry'}
            </span>

            <div style={{ display: 'flex', gap: '8px' }}>
              <Button variant="ghost" size="sm" type="button" onClick={handleRequestClose} disabled={isSubmitting}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" type="submit" isLoading={isSubmitting}>
                {isEditing ? 'Save Changes' : 'Create Defense Zone'}
              </Button>
            </div>
          </div>
        </form>

        {/* Unsaved Changes Confirmation Dialog */}
        {showUnsavedWarning && (
          <div
            style={{
              position: 'absolute',
              inset: 0,
              backgroundColor: 'rgba(2, 6, 12, 0.85)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              padding: '16px',
            }}
          >
            <div
              style={{
                backgroundColor: 'var(--bg-surface)',
                border: '1px solid var(--border-medium)',
                borderRadius: 'var(--radius-md)',
                padding: '16px',
                maxWidth: '400px',
                display: 'flex',
                flexDirection: 'column',
                gap: '12px',
              }}
            >
              <h3 className="font-mono text-sm" style={{ margin: 0, color: 'var(--status-warning)' }}>
                ⚠ Unsaved Changes Detected
              </h3>
              <p className="text-muted text-xs" style={{ margin: 0, lineHeight: 1.4 }}>
                You have unsaved changes to this defense zone configuration. Discarding will lose all modified coordinates and boundary settings.
              </p>
              <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px' }}>
                <Button variant="secondary" size="sm" onClick={() => setShowUnsavedWarning(false)}>
                  Continue Editing
                </Button>
                <Button variant="danger" size="sm" onClick={handleConfirmDiscard}>
                  Discard Changes
                </Button>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
