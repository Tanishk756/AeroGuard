import React, { useEffect, useState } from 'react';
import {
  Geofence,
  Scenario,
  ScenarioConfiguration,
  ScenarioCreate,
  ScenarioSensorDefinition,
  ScenarioTargetDefinition,
  ScenarioUpdate,
} from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { SensorConfigForm } from './SensorConfigForm';
import { TargetConfigForm } from './TargetConfigForm';

interface ScenarioEditorModalProps {
  isOpen: boolean;
  initialScenario?: Scenario | null;
  isCloneMode?: boolean;
  availableGeofences?: Geofence[];
  onClose: () => void;
  onSave: (data: ScenarioCreate | ScenarioUpdate) => Promise<void>;
}

type EditorTab = 'general' | 'targets' | 'sensors' | 'geofences';

export const ScenarioEditorModal: React.FC<ScenarioEditorModalProps> = ({
  isOpen,
  initialScenario,
  isCloneMode = false,
  availableGeofences = [],
  onClose,
  onSave,
}) => {
  const isEditing = !!initialScenario && !isCloneMode;
  const isExecutionBlocked =
    isEditing &&
    (initialScenario?.status === 'RUNNING' || initialScenario?.status === 'PAUSED');

  const [activeTab, setActiveTab] = useState<EditorTab>('general');

  // General fields
  const [name, setName] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [durationSeconds, setDurationSeconds] = useState<number>(300);
  const [tickRateHz, setTickRateHz] = useState<number>(1.0);
  const [seed, setSeed] = useState<number>(1337);
  const [startTime, setStartTime] = useState<string>('2026-01-01T00:00:00');

  // Targets & Sensors
  const [targets, setTargets] = useState<ScenarioTargetDefinition[]>([]);
  const [sensors, setSensors] = useState<ScenarioSensorDefinition[]>([]);
  const [selectedGeofenceIds, setSelectedGeofenceIds] = useState<string[]>([]);

  // Safety & State management
  const [isDirty, setIsDirty] = useState<boolean>(false);
  const [showUnsavedWarning, setShowUnsavedWarning] = useState<boolean>(false);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = useState<boolean>(false);

  // Initialize form state
  useEffect(() => {
    if (isOpen) {
      if (initialScenario) {
        const meta = (initialScenario.configuration_metadata || {}) as Record<string, unknown>;
        const config = (meta.configuration || meta) as Partial<ScenarioConfiguration>;

        setName(isCloneMode ? `${initialScenario.name} (Copy)` : initialScenario.name);
        setDescription(initialScenario.description || '');
        setDurationSeconds(typeof config.duration_seconds === 'number' ? config.duration_seconds : 300);
        setTickRateHz(typeof config.tick_rate_hz === 'number' ? config.tick_rate_hz : 1.0);
        setSeed(typeof config.seed === 'number' ? config.seed : 1337);
        setStartTime(
          typeof config.start_time === 'string'
            ? config.start_time.substring(0, 19)
            : '2026-01-01T00:00:00'
        );
        setTargets(Array.isArray(config.targets) ? config.targets : []);
        setSensors(Array.isArray(config.sensors) ? config.sensors : []);
        setSelectedGeofenceIds(Array.isArray(config.geofence_ids) ? config.geofence_ids : []);
      } else {
        // Default new scenario with 1 target and 1 radar sensor
        setName('');
        setDescription('');
        setDurationSeconds(300);
        setTickRateHz(1.0);
        setSeed(Math.floor(Math.random() * 100000));
        setStartTime('2026-01-01T00:00:00');
        setTargets([
          {
            target_id: 'TARGET-01',
            classification: 'DRONE_ROTARY',
            initial_latitude: 37.7749,
            initial_longitude: -122.4194,
            initial_altitude: 120.0,
            velocity: 15.0,
            heading: 90.0,
            waypoints: [],
          },
        ]);
        setSensors([
          {
            sensor_id: 'SIM-RADAR-01',
            modality: 'radar',
            latitude: 37.7749,
            longitude: -122.4194,
            altitude: 10.0,
            range_meters: 5000.0,
            detection_probability: 0.95,
            position_uncertainty_meters: 5.0,
            fov_azimuth_start_deg: 0,
            fov_azimuth_span_deg: 360,
          },
        ]);
        setSelectedGeofenceIds([]);
      }
      setIsDirty(false);
      setShowUnsavedWarning(false);
      setValidationError(null);
      setActiveTab('general');
    }
  }, [isOpen, initialScenario, isCloneMode]);

  const markDirty = () => setIsDirty(true);

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

  const toggleGeofenceSelection = (geofenceId: string) => {
    setSelectedGeofenceIds((prev) =>
      prev.includes(geofenceId) ? prev.filter((id) => id !== geofenceId) : [...prev, geofenceId]
    );
    markDirty();
  };

  // Submit Handler
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setValidationError(null);

    if (isExecutionBlocked) {
      setValidationError('Active simulation runs cannot be re-configured while executing. Please stop or reset the scenario before editing.');
      return;
    }

    const trimmedName = name.trim();
    if (!trimmedName) {
      setValidationError('Scenario name is required.');
      return;
    }

    if (durationSeconds <= 0 || durationSeconds > 86400) {
      setValidationError('Duration must be between 1 and 86,400 seconds (24 hours).');
      return;
    }

    if (tickRateHz <= 0 || tickRateHz > 100) {
      setValidationError('Tick rate must be between 0.1 and 100.0 Hz.');
      return;
    }

    // Validate unique target IDs
    const targetIds = targets.map((t) => t.target_id.trim());
    if (new Set(targetIds).size !== targetIds.length) {
      setValidationError('All synthetic target IDs must be unique.');
      return;
    }

    // Validate unique sensor IDs
    const sensorIds = sensors.map((s) => s.sensor_id.trim());
    if (new Set(sensorIds).size !== sensorIds.length) {
      setValidationError('All synthetic sensor IDs must be unique.');
      return;
    }

    const configPayload: ScenarioConfiguration = {
      seed,
      duration_seconds: durationSeconds,
      tick_rate_hz: tickRateHz,
      start_time: startTime.includes('Z') ? startTime : `${startTime}Z`,
      targets,
      sensors,
      geofence_ids: selectedGeofenceIds,
    };

    const payload: ScenarioCreate | ScenarioUpdate = {
      name: trimmedName,
      description: description.trim(),
      configuration: configPayload,
    };

    setIsSubmitting(true);
    try {
      await onSave(payload);
      setIsDirty(false);
      onClose();
    } catch (err: unknown) {
      setValidationError(err instanceof Error ? err.message : 'Failed to save scenario configuration.');
    } finally {
      setIsSubmitting(false);
    }
  };

  if (!isOpen) return null;

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-labelledby="scenario-editor-title"
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
          maxWidth: '780px',
          maxHeight: '92vh',
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
            <span style={{ width: '8px', height: '8px', backgroundColor: 'var(--color-accent)', borderRadius: '1px' }} />
            <h2 id="scenario-editor-title" className="font-mono text-sm" style={{ fontWeight: 700, margin: 0, color: 'var(--text-primary)' }}>
              {isCloneMode
                ? `CLONE SCENARIO TEMPLATE: ${initialScenario?.name}`
                : isEditing
                ? `EDIT SCENARIO CONFIGURATION: ${initialScenario?.name}`
                : 'AUTHOR NEW SIMULATION SCENARIO'}
            </h2>
          </div>
          <Button variant="ghost" size="sm" onClick={handleRequestClose} style={{ padding: '2px 6px', fontSize: '11px' }}>
            ✕
          </Button>
        </div>

        {/* Studio Navigation Tabs */}
        <div style={{ display: 'flex', gap: '4px', padding: '8px 16px 0', borderBottom: '1px solid var(--border-subtle)', backgroundColor: 'var(--bg-canvas)' }}>
          <button
            type="button"
            className="tactical-btn"
            onClick={() => setActiveTab('general')}
            style={{
              backgroundColor: activeTab === 'general' ? 'var(--bg-surface-active)' : 'transparent',
              color: activeTab === 'general' ? 'var(--color-accent)' : 'var(--text-secondary)',
              borderColor: activeTab === 'general' ? 'var(--color-accent)' : 'transparent',
              padding: '4px 10px',
              fontSize: '11px',
            }}
          >
            1. General & Clock
          </button>
          <button
            type="button"
            className="tactical-btn"
            onClick={() => setActiveTab('targets')}
            style={{
              backgroundColor: activeTab === 'targets' ? 'var(--bg-surface-active)' : 'transparent',
              color: activeTab === 'targets' ? 'var(--color-accent)' : 'var(--text-secondary)',
              borderColor: activeTab === 'targets' ? 'var(--color-accent)' : 'transparent',
              padding: '4px 10px',
              fontSize: '11px',
            }}
          >
            2. Targets & Kinematics ({targets.length})
          </button>
          <button
            type="button"
            className="tactical-btn"
            onClick={() => setActiveTab('sensors')}
            style={{
              backgroundColor: activeTab === 'sensors' ? 'var(--bg-surface-active)' : 'transparent',
              color: activeTab === 'sensors' ? 'var(--color-accent)' : 'var(--text-secondary)',
              borderColor: activeTab === 'sensors' ? 'var(--color-accent)' : 'transparent',
              padding: '4px 10px',
              fontSize: '11px',
            }}
          >
            3. Sensors & Modalities ({sensors.length})
          </button>
          <button
            type="button"
            className="tactical-btn"
            onClick={() => setActiveTab('geofences')}
            style={{
              backgroundColor: activeTab === 'geofences' ? 'var(--bg-surface-active)' : 'transparent',
              color: activeTab === 'geofences' ? 'var(--color-accent)' : 'var(--text-secondary)',
              borderColor: activeTab === 'geofences' ? 'var(--color-accent)' : 'transparent',
              padding: '4px 10px',
              fontSize: '11px',
            }}
          >
            4. Defense Zones ({selectedGeofenceIds.length})
          </button>
        </div>

        {/* Form Body */}
        <form onSubmit={handleSubmit} style={{ overflowY: 'auto', padding: '16px', display: 'flex', flexDirection: 'column', gap: '14px', flex: 1 }}>
          {isExecutionBlocked && (
            <div style={{ padding: '8px 12px', backgroundColor: 'var(--status-critical-bg)', border: '1px solid var(--status-critical-border)', borderRadius: 'var(--radius-sm)', color: 'var(--status-critical)', fontSize: '11px', fontFamily: 'monospace' }}>
              🔒 Execution Guard: Scenario is currently in {initialScenario?.status} state. Stop or reset the simulation before re-configuring.
            </div>
          )}

          {validationError && (
            <div style={{ padding: '8px 12px', backgroundColor: 'var(--status-critical-bg)', border: '1px solid var(--status-critical-border)', borderRadius: 'var(--radius-sm)', color: 'var(--status-critical)', fontSize: '11px', fontFamily: 'monospace' }}>
              ⚠ {validationError}
            </div>
          )}

          {/* Tab 1: General Parameters */}
          {activeTab === 'general' && (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
              <div style={{ display: 'grid', gridTemplateColumns: '1.4fr 1fr', gap: '10px' }}>
                <div>
                  <label className="text-muted text-xs uppercase-tracking" style={{ display: 'block', marginBottom: '2px' }}>
                    Scenario Name *
                  </label>
                  <input
                    type="text"
                    className="tactical-input font-mono"
                    value={name}
                    onChange={(e) => {
                      setName(e.target.value);
                      markDirty();
                    }}
                    placeholder="e.g. MULTI_UAV_PERIMETER_PROBE"
                    required
                  />
                </div>

                <div>
                  <label className="text-muted text-xs uppercase-tracking" style={{ display: 'block', marginBottom: '2px' }}>
                    Random Seed (Determinism)
                  </label>
                  <input
                    type="number"
                    step="1"
                    min="0"
                    className="tactical-input font-mono"
                    value={seed}
                    onChange={(e) => {
                      setSeed(parseInt(e.target.value, 10) || 0);
                      markDirty();
                    }}
                    required
                  />
                </div>
              </div>

              <div>
                <label className="text-muted text-xs uppercase-tracking" style={{ display: 'block', marginBottom: '2px' }}>
                  Operational Description
                </label>
                <textarea
                  className="tactical-input font-mono"
                  rows={2}
                  value={description}
                  onChange={(e) => {
                    setDescription(e.target.value);
                    markDirty();
                  }}
                  placeholder="Describe simulation scenario objectives and test conditions..."
                />
              </div>

              <Card title="Simulation Engine Clock Parameters">
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1.2fr', gap: '10px' }}>
                  <div>
                    <label className="text-muted text-xs uppercase-tracking">Duration (seconds)</label>
                    <input
                      type="number"
                      step="10"
                      min="1"
                      max="86400"
                      className="tactical-input font-mono"
                      value={durationSeconds}
                      onChange={(e) => {
                        setDurationSeconds(Math.max(1, parseFloat(e.target.value) || 1));
                        markDirty();
                      }}
                      required
                    />
                  </div>

                  <div>
                    <label className="text-muted text-xs uppercase-tracking">Tick Rate (Hz)</label>
                    <input
                      type="number"
                      step="0.5"
                      min="0.1"
                      max="100"
                      className="tactical-input font-mono"
                      value={tickRateHz}
                      onChange={(e) => {
                        setTickRateHz(Math.max(0.1, parseFloat(e.target.value) || 1.0));
                        markDirty();
                      }}
                      required
                    />
                  </div>

                  <div>
                    <label className="text-muted text-xs uppercase-tracking">Simulation Start Time (UTC)</label>
                    <input
                      type="datetime-local"
                      className="tactical-input font-mono"
                      value={startTime}
                      onChange={(e) => {
                        setStartTime(e.target.value);
                        markDirty();
                      }}
                      required
                    />
                  </div>
                </div>
              </Card>
            </div>
          )}

          {/* Tab 2: Targets */}
          {activeTab === 'targets' && (
            <TargetConfigForm
              targets={targets}
              onChange={(updated) => {
                setTargets(updated);
                markDirty();
              }}
            />
          )}

          {/* Tab 3: Sensors */}
          {activeTab === 'sensors' && (
            <SensorConfigForm
              sensors={sensors}
              onChange={(updated) => {
                setSensors(updated);
                markDirty();
              }}
            />
          )}

          {/* Tab 4: Geofences */}
          {activeTab === 'geofences' && (
            <Card
              title="Defense Zone Association (Automated Breach Evaluation)"
              badge={<span className="font-mono text-xs text-muted">{selectedGeofenceIds.length} ATTACHED</span>}
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <p className="text-muted text-xs font-mono" style={{ margin: 0 }}>
                  Select defense zones to associate with this simulation. The engine will evaluate geometric breaches and trigger operational alerts when targets enter exclusion zones or exit inclusion zones.
                </p>

                {availableGeofences.length === 0 ? (
                  <p className="text-muted text-xs font-mono" style={{ padding: '8px', backgroundColor: 'var(--bg-canvas)' }}>
                    No defense zones registered. You can author defense zones in the Defense Zones tab.
                  </p>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '6px', maxHeight: '240px', overflowY: 'auto' }}>
                    {availableGeofences.map((g) => {
                      const isSelected = selectedGeofenceIds.includes(g.id);
                      return (
                        <div
                          key={g.id}
                          onClick={() => toggleGeofenceSelection(g.id)}
                          style={{
                            padding: '6px 8px',
                            backgroundColor: isSelected ? 'var(--bg-surface-active)' : 'var(--bg-canvas)',
                            border: isSelected ? '1px solid var(--color-accent)' : '1px solid var(--border-subtle)',
                            borderRadius: 'var(--radius-sm)',
                            cursor: 'pointer',
                            display: 'flex',
                            alignItems: 'center',
                            justifyContent: 'space-between',
                          }}
                        >
                          <div>
                            <div className="font-mono text-xs" style={{ fontWeight: 600, color: isSelected ? 'var(--color-accent)' : 'var(--text-primary)' }}>
                              {g.name}
                            </div>
                            <div className="text-muted" style={{ fontSize: '9px' }}>
                              {g.geometry.type.toUpperCase()} • {String(g.metadata?.rule || 'EXCLUSION')}
                            </div>
                          </div>
                          <span style={{ fontSize: '12px' }}>{isSelected ? '✓' : '+'}</span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </div>
            </Card>
          )}

          {/* Footer Actions */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginTop: 'auto', paddingTop: '10px', borderTop: '1px solid var(--border-subtle)' }}>
            <span className="font-mono text-xs text-muted">
              Targets: {targets.length} • Sensors: {sensors.length} • Zones: {selectedGeofenceIds.length}
            </span>

            <div style={{ display: 'flex', gap: '8px' }}>
              <Button variant="ghost" size="sm" type="button" onClick={handleRequestClose} disabled={isSubmitting}>
                Cancel
              </Button>
              <Button variant="primary" size="sm" type="submit" isLoading={isSubmitting} disabled={isExecutionBlocked}>
                {isCloneMode ? 'Create Cloned Scenario' : isEditing ? 'Save Configuration' : 'Create Simulation Scenario'}
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
                You have unsaved changes in this scenario builder studio. Discarding will lose all configured targets, waypoints, and sensor parameters.
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
