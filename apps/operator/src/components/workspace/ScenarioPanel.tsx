import React, { useCallback, useEffect, useState } from 'react';
import { getGeofences } from '../../api/geofences';
import {
  createScenario,
  deleteScenario,
  getScenarios,
  getScenarioStatus,
  pauseScenario,
  prepareScenario,
  resetScenario,
  resumeScenario,
  startScenario,
  stepScenario,
  stopScenario,
  updateScenario,
} from '../../api/scenarios';
import { useAuth } from '../../context/AuthContext';
import { Geofence, Scenario, ScenarioCreate, ScenarioExecutionStatus, ScenarioUpdate } from '../../types';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { EmptyState } from '../common/EmptyState';
import { ErrorState } from '../common/ErrorState';
import { LoadingState } from '../common/LoadingState';
import { StatusBadge } from '../common/StatusBadge';
import { ScenarioEditorModal } from '../scenario/ScenarioEditorModal';

interface ScenarioPanelProps {
  onSelectScenario?: (scenario: Scenario) => void;
  selectedScenarioId?: string | null;
}

export const ScenarioPanel: React.FC<ScenarioPanelProps> = ({
  onSelectScenario,
  selectedScenarioId: externalSelectedId,
}) => {
  const { hasPermission, hasAnyPermission } = useAuth();
  const canRunScenarios = hasAnyPermission(['scenarios.run', 'scenarios.execute']);
  const canCreateScenarios = hasPermission('scenarios.create');
  const canUpdateScenarios = hasPermission('scenarios.update');
  const canDeleteScenarios = hasPermission('scenarios.delete');

  const [scenarios, setScenarios] = useState<Scenario[]>([]);
  const [selectedScenario, setSelectedScenario] = useState<Scenario | null>(null);
  const [status, setStatus] = useState<ScenarioExecutionStatus | null>(null);
  const [geofences, setGeofences] = useState<Geofence[]>([]);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [isActionPending, setIsActionPending] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [actionSuccess, setActionSuccess] = useState<string | null>(null);

  // Authoring / Builder modal state
  const [isEditorOpen, setIsEditorOpen] = useState<boolean>(false);
  const [editorScenario, setEditorScenario] = useState<Scenario | null>(null);
  const [isCloneMode, setIsCloneMode] = useState<boolean>(false);

  // Destructive deletion modal state (Two-step confirmation)
  const [deletingScenario, setDeletingScenario] = useState<Scenario | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  const fetchScenarios = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const [scenariosRes, geofencesRes] = await Promise.all([
        getScenarios({ limit: 50 }),
        getGeofences({ limit: 100 }),
      ]);
      setScenarios(scenariosRes.items || []);
      setGeofences(geofencesRes.items || []);

      if (scenariosRes.items && scenariosRes.items.length > 0) {
        if (externalSelectedId) {
          const match = scenariosRes.items.find((s) => s.id === externalSelectedId);
          setSelectedScenario(match || scenariosRes.items[0]);
        } else if (!selectedScenario) {
          setSelectedScenario(scenariosRes.items[0]);
        }
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to query scenarios');
    } finally {
      setIsLoading(false);
    }
  }, [externalSelectedId, selectedScenario]);

  useEffect(() => {
    fetchScenarios();
  }, [fetchScenarios]);

  // Fetch execution status for the selected scenario
  const fetchStatus = useCallback(async (scenarioId: string) => {
    try {
      const res = await getScenarioStatus(scenarioId);
      setStatus(res);
    } catch {
      setStatus(null);
    }
  }, []);

  useEffect(() => {
    if (selectedScenario) {
      fetchStatus(selectedScenario.id);
      onSelectScenario?.(selectedScenario);
    } else {
      setStatus(null);
    }
  }, [selectedScenario, fetchStatus, onSelectScenario]);

  const handleAction = async (actionFn: () => Promise<ScenarioExecutionStatus | Scenario>, name: string) => {
    setIsActionPending(true);
    setError(null);
    setActionSuccess(null);
    try {
      await actionFn();
      setActionSuccess(`Scenario action '${name}' completed successfully.`);
      if (selectedScenario) {
        await fetchStatus(selectedScenario.id);
        const res = await getScenarios({ limit: 50 });
        setScenarios(res.items || []);
        const updated = (res.items || []).find((s) => s.id === selectedScenario.id);
        if (updated) setSelectedScenario(updated);
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : `Action '${name}' failed`);
    } finally {
      setIsActionPending(false);
    }
  };

  // Authoring Save Handler (Create, Edit, Clone)
  const handleSaveScenario = async (data: ScenarioCreate | ScenarioUpdate) => {
    setError(null);
    setActionSuccess(null);
    if (editorScenario && !isCloneMode) {
      const updated = await updateScenario(editorScenario.id, data as ScenarioUpdate);
      setActionSuccess(`Scenario '${updated.name}' updated successfully.`);
    } else {
      const created = await createScenario(data as ScenarioCreate);
      setActionSuccess(`Scenario '${created.name}' created successfully.`);
    }
    await fetchScenarios();
  };

  // Destructive Deletion Handler
  const handleConfirmDelete = async () => {
    if (!deletingScenario) return;
    setIsDeleting(true);
    setError(null);
    setActionSuccess(null);
    try {
      await deleteScenario(deletingScenario.id);
      setActionSuccess(`Scenario '${deletingScenario.name}' permanently deleted.`);
      setDeletingScenario(null);
      if (selectedScenario?.id === deletingScenario.id) {
        setSelectedScenario(null);
      }
      await fetchScenarios();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to delete scenario');
    } finally {
      setIsDeleting(false);
    }
  };

  const currentStatus = status?.status || selectedScenario?.status || 'READY';
  const isRunning = currentStatus === 'RUNNING';
  const isPaused = currentStatus === 'PAUSED';
  const isReady = currentStatus === 'READY' || currentStatus === 'DRAFT';
  const isStopped = currentStatus === 'STOPPED' || currentStatus === 'COMPLETED';
  const isExecutionActive = isRunning || isPaused;

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
      {error && <ErrorState message={error} onRetry={() => selectedScenario && fetchStatus(selectedScenario.id)} />}

      {actionSuccess && (
        <div
          style={{
            padding: '6px 10px',
            backgroundColor: 'var(--status-success-bg)',
            border: '1px solid var(--status-success-border)',
            borderRadius: 'var(--radius-sm)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
        >
          <span className="font-mono text-xs" style={{ color: 'var(--status-success)', fontWeight: 600 }}>
            ✓ {actionSuccess}
          </span>
          <Button variant="ghost" size="sm" onClick={() => setActionSuccess(null)} style={{ padding: '0 4px', fontSize: '10px' }}>
            ✕
          </Button>
        </div>
      )}

      {/* Main Split Layout: Scenario Directory + Execution Hub */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 1fr) minmax(360px, 1.4fr)', gap: 'var(--space-md)' }}>
        {/* Scenario List */}
        <Card
          title="Simulation Scenarios (F5 Engine)"
          badge={<span className="font-mono text-xs text-muted">TOTAL: {scenarios.length}</span>}
          actions={
            canCreateScenarios ? (
              <Button
                variant="primary"
                size="sm"
                onClick={() => {
                  setEditorScenario(null);
                  setIsCloneMode(false);
                  setIsEditorOpen(true);
                }}
                style={{ padding: '2px 8px', fontSize: '11px' }}
              >
                + New Scenario
              </Button>
            ) : undefined
          }
          bodyStyle={{ padding: 0 }}
        >
          {isLoading && scenarios.length === 0 ? (
            <LoadingState message="Loading simulation scenarios..." />
          ) : scenarios.length === 0 ? (
            <EmptyState title="No Scenarios Registered" description="No simulation scenarios are registered in the backend." />
          ) : (
            <div className="tactical-table-wrapper" style={{ maxHeight: '440px' }}>
              <table className="tactical-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Status</th>
                    <th>Created</th>
                  </tr>
                </thead>
                <tbody>
                  {scenarios.map((s) => {
                    const isSelected = selectedScenario?.id === s.id;
                    return (
                      <tr
                        key={s.id}
                        onClick={() => setSelectedScenario(s)}
                        style={{
                          cursor: 'pointer',
                          backgroundColor: isSelected ? 'var(--bg-surface-active)' : undefined,
                        }}
                      >
                        <td>
                          <div style={{ fontWeight: 600, color: 'var(--text-primary)' }}>{s.name}</div>
                          {s.description && (
                            <div className="text-muted text-xs" style={{ maxWidth: '180px', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                              {s.description}
                            </div>
                          )}
                        </td>
                        <td>
                          <StatusBadge status={s.status} />
                        </td>
                        <td className="font-mono text-xs text-muted">{s.created_at.substring(0, 10)}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        {/* Selected Scenario Execution & Control Hub */}
        {selectedScenario ? (
          <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
            {/* Scenario Header & Execution Controls */}
            <Card
              title={`Execution Hub: ${selectedScenario.name}`}
              badge={<StatusBadge status={currentStatus} />}
              actions={
                <div style={{ display: 'flex', gap: '4px' }}>
                  {canCreateScenarios && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setEditorScenario(selectedScenario);
                        setIsCloneMode(true);
                        setIsEditorOpen(true);
                      }}
                      style={{ padding: '2px 6px', fontSize: '10px' }}
                    >
                      Clone Template
                    </Button>
                  )}
                  {canUpdateScenarios && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => {
                        setEditorScenario(selectedScenario);
                        setIsCloneMode(false);
                        setIsEditorOpen(true);
                      }}
                      disabled={isExecutionActive}
                      title={isExecutionActive ? 'Cannot edit active simulation run' : 'Edit Scenario Configuration'}
                      style={{ padding: '2px 6px', fontSize: '10px' }}
                    >
                      Edit Config
                    </Button>
                  )}
                  {canDeleteScenarios && (
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => setDeletingScenario(selectedScenario)}
                      disabled={isExecutionActive}
                      title={isExecutionActive ? 'Cannot delete active simulation run' : 'Delete Scenario'}
                      style={{ padding: '2px 6px', fontSize: '10px' }}
                    >
                      Delete
                    </Button>
                  )}
                </div>
              }
            >
              <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
                {/* Control Action Toolbar */}
                <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-xs)', alignItems: 'center' }}>
                  {isReady && (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleAction(() => startScenario(selectedScenario.id), 'Start Scenario')}
                      disabled={!canRunScenarios || isActionPending}
                      isLoading={isActionPending}
                    >
                      ▶ Start Simulation
                    </Button>
                  )}

                  {isRunning && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => handleAction(() => pauseScenario(selectedScenario.id), 'Pause')}
                      disabled={!canRunScenarios || isActionPending}
                      isLoading={isActionPending}
                    >
                      ⏸ Pause
                    </Button>
                  )}

                  {isPaused && (
                    <Button
                      variant="primary"
                      size="sm"
                      onClick={() => handleAction(() => resumeScenario(selectedScenario.id), 'Resume')}
                      disabled={!canRunScenarios || isActionPending}
                      isLoading={isActionPending}
                    >
                      ▶ Resume
                    </Button>
                  )}

                  {(isPaused || isReady) && (
                    <>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleAction(() => stepScenario(selectedScenario.id, 1), 'Step +1 Tick')}
                        disabled={!canRunScenarios || isActionPending}
                        isLoading={isActionPending}
                      >
                        ⏭ Step +1 Tick
                      </Button>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleAction(() => stepScenario(selectedScenario.id, 5), 'Step +5 Ticks')}
                        disabled={!canRunScenarios || isActionPending}
                        isLoading={isActionPending}
                      >
                        ⏭ Step +5 Ticks
                      </Button>
                    </>
                  )}

                  {(isRunning || isPaused) && (
                    <Button
                      variant="danger"
                      size="sm"
                      onClick={() => handleAction(() => stopScenario(selectedScenario.id), 'Stop')}
                      disabled={!canRunScenarios || isActionPending}
                      isLoading={isActionPending}
                    >
                      ⏹ Stop
                    </Button>
                  )}

                  {isStopped && (
                    <>
                      <Button
                        variant="secondary"
                        size="sm"
                        onClick={() => handleAction(() => resetScenario(selectedScenario.id), 'Reset')}
                        disabled={!canRunScenarios || isActionPending}
                        isLoading={isActionPending}
                      >
                        ↺ Reset to Beginning
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => handleAction(() => prepareScenario(selectedScenario.id), 'Prepare Session')}
                        disabled={!canRunScenarios || isActionPending}
                        isLoading={isActionPending}
                      >
                        ⚙ Prepare
                      </Button>
                    </>
                  )}

                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={() => fetchStatus(selectedScenario.id)}
                    disabled={isActionPending}
                    style={{ marginLeft: 'auto' }}
                  >
                    Refresh Status
                  </Button>
                </div>

                {!canRunScenarios && (
                  <div
                    style={{
                      padding: '4px 8px',
                      backgroundColor: 'var(--status-warning-bg)',
                      border: '1px solid var(--status-warning-border)',
                      borderRadius: 'var(--radius-sm)',
                    }}
                  >
                    <span className="font-mono text-xs" style={{ color: '#fcd34d' }}>
                      ℹ View-only mode: Role requires 'scenarios.run' permission to execute simulation clock.
                    </span>
                  </div>
                )}

                {/* Real-time Virtual Clock & Simulation Telemetry */}
                {status && (
                  <div
                    style={{
                      padding: 'var(--space-sm) var(--space-md)',
                      backgroundColor: 'var(--bg-canvas)',
                      border: '1px solid var(--border-subtle)',
                      borderRadius: 'var(--radius-sm)',
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(140px, 1fr))',
                      gap: 'var(--space-sm)',
                    }}
                  >
                    <div>
                      <div className="text-muted text-xs uppercase-tracking">Virtual Clock</div>
                      <div className="font-mono text-sm" style={{ fontWeight: 700, color: 'var(--color-accent)' }}>
                        {status.virtual_time ? status.virtual_time.substring(11, 19) + ' UTC' : '00:00:00 UTC'}
                      </div>
                    </div>

                    <div>
                      <div className="text-muted text-xs uppercase-tracking">Simulation Ticks</div>
                      <div className="font-mono text-sm" style={{ fontWeight: 600 }}>
                        {status.tick_count} ticks
                      </div>
                    </div>

                    <div>
                      <div className="text-muted text-xs uppercase-tracking">Active Targets</div>
                      <div className="font-mono text-sm" style={{ fontWeight: 600, color: 'var(--status-info)' }}>
                        {status.active_targets}
                      </div>
                    </div>

                    <div>
                      <div className="text-muted text-xs uppercase-tracking">Generated Detections</div>
                      <div className="font-mono text-sm" style={{ fontWeight: 600 }}>
                        {status.generated_detections_count}
                      </div>
                    </div>
                  </div>
                )}
              </div>
            </Card>

            {/* Scenario Configuration Metadata */}
            <Card title="Deterministic Simulation Specification">
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 'var(--space-xs)' }}>
                <div className="kv-row">
                  <span className="kv-key">Scenario ID</span>
                  <span className="kv-value font-mono text-xs text-muted">{selectedScenario.id}</span>
                </div>
                <div className="kv-row">
                  <span className="kv-key">Source Class</span>
                  <span className="kv-value font-mono">{selectedScenario.source_class}</span>
                </div>
                <div className="kv-row">
                  <span className="kv-key">Created By</span>
                  <span className="kv-value font-mono text-xs text-muted">{selectedScenario.created_by_user_id}</span>
                </div>
                <div className="kv-row">
                  <span className="kv-key">Config Status</span>
                  <span className="kv-value font-mono">{selectedScenario.status}</span>
                </div>
              </div>
            </Card>
          </div>
        ) : (
          <Card title="Scenario Inspection">
            <EmptyState title="No Scenario Selected" description="Select a simulation scenario from the list to view configuration and execution controls." />
          </Card>
        )}
      </div>

      {/* Scenario Authoring & Simulation Builder Modal */}
      <ScenarioEditorModal
        isOpen={isEditorOpen}
        initialScenario={editorScenario}
        isCloneMode={isCloneMode}
        availableGeofences={geofences}
        onClose={() => {
          setIsEditorOpen(false);
          setEditorScenario(null);
          setIsCloneMode(false);
        }}
        onSave={handleSaveScenario}
      />

      {/* Two-Step Destructive Deletion Confirmation Modal */}
      {deletingScenario && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Confirm Scenario Deletion"
          style={{
            position: 'fixed',
            inset: 0,
            backgroundColor: 'rgba(2, 6, 12, 0.85)',
            backdropFilter: 'blur(2px)',
            zIndex: 9999,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: '16px',
          }}
        >
          <div
            style={{
              backgroundColor: 'var(--bg-surface-elevated)',
              border: '1px solid var(--status-critical-border)',
              borderRadius: 'var(--radius-md)',
              padding: '20px',
              maxWidth: '440px',
              width: '100%',
              display: 'flex',
              flexDirection: 'column',
              gap: '14px',
              boxShadow: 'var(--shadow-lg)',
            }}
          >
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ color: 'var(--status-critical)', fontSize: '18px' }}>⚠</span>
              <h3 className="font-mono text-sm" style={{ margin: 0, fontWeight: 700, color: 'var(--text-primary)' }}>
                CONFIRM DESTRUCTIVE SCENARIO DELETION
              </h3>
            </div>

            <p className="text-muted text-xs" style={{ margin: 0, lineHeight: 1.4 }}>
              Are you sure you want to permanently delete simulation scenario{' '}
              <strong className="font-mono" style={{ color: 'var(--color-accent)' }}>{deletingScenario.name}</strong>?
              All configured synthetic targets, waypoints, and sensor trajectories will be permanently removed.
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '4px' }}>
              <Button variant="ghost" size="sm" onClick={() => setDeletingScenario(null)} disabled={isDeleting}>
                Cancel
              </Button>
              <Button variant="danger" size="sm" onClick={handleConfirmDelete} isLoading={isDeleting}>
                Permanently Delete Scenario
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
