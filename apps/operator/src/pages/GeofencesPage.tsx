import React, { useCallback, useEffect, useState } from 'react';
import { createGeofence, deleteGeofence, getGeofences, updateGeofence } from '../api/geofences';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { LoadingState } from '../components/common/LoadingState';
import { StatusBadge } from '../components/common/StatusBadge';
import { GeofenceEditor } from '../components/geofence/GeofenceEditor';
import { useAuth } from '../context/AuthContext';
import { Geofence, GeofenceCreate, GeofenceGeometry, GeofenceUpdate } from '../types';

export const GeofencesPage: React.FC = () => {
  const { hasPermission } = useAuth();
  const canCreate = hasPermission('scenarios.create');
  const canUpdate = hasPermission('scenarios.update');
  const canDelete = hasPermission('scenarios.delete');

  const [geofences, setGeofences] = useState<Geofence[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [ruleFilter, setRuleFilter] = useState<string>('');
  const [typeFilter, setTypeFilter] = useState<string>('');

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState<string | null>(null);

  // Editor Modal state
  const [isEditorOpen, setIsEditorOpen] = useState<boolean>(false);
  const [editingGeofence, setEditingGeofence] = useState<Geofence | null>(null);

  // Deletion Modal state (Two-step destructive confirmation)
  const [deletingGeofence, setDeletingGeofence] = useState<Geofence | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  const fetchGeofences = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await getGeofences({
        enabled: statusFilter === 'ENABLED' ? true : statusFilter === 'DISABLED' ? false : undefined,
      });
      setGeofences(res.items);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to query geofences');
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchGeofences();
  }, [fetchGeofences]);

  // Filter client-side for rule & type
  const filteredGeofences = geofences.filter((g) => {
    if (ruleFilter && g.metadata?.rule !== ruleFilter) return false;
    if (typeFilter && g.geometry.type !== typeFilter) return false;
    return true;
  });

  // Handle Save (Create or Update)
  const handleSaveGeofence = async (data: GeofenceCreate | GeofenceUpdate) => {
    setError(null);
    setSuccessMsg(null);
    if (editingGeofence) {
      await updateGeofence(editingGeofence.id, data as GeofenceUpdate);
      setSuccessMsg(`Defense zone '${data.name || editingGeofence.name}' updated successfully.`);
    } else {
      const created = await createGeofence(data as GeofenceCreate);
      setSuccessMsg(`Defense zone '${created.name}' created successfully.`);
    }
    await fetchGeofences();
  };

  // Toggle enabled/disabled status
  const handleToggleEnabled = async (g: Geofence) => {
    if (!canUpdate) return;
    setError(null);
    setSuccessMsg(null);
    try {
      await updateGeofence(g.id, { enabled: !g.enabled });
      setSuccessMsg(`Zone '${g.name}' set to ${!g.enabled ? 'ENABLED' : 'DISABLED'}.`);
      await fetchGeofences();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to update zone status');
    }
  };

  // Execute two-step confirmed deletion
  const handleConfirmDelete = async () => {
    if (!deletingGeofence) return;
    setIsDeleting(true);
    setError(null);
    setSuccessMsg(null);
    try {
      await deleteGeofence(deletingGeofence.id);
      setSuccessMsg(`Zone '${deletingGeofence.name}' permanently deleted.`);
      setDeletingGeofence(null);
      await fetchGeofences();
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to delete geofence');
    } finally {
      setIsDeleting(false);
    }
  };

  // Metrics
  const totalCount = geofences.length;
  const activeCount = geofences.filter((g) => g.enabled).length;
  const inclusionCount = geofences.filter((g) => g.metadata?.rule === 'INCLUSION').length;
  const altitudeBoundedCount = geofences.filter((g) => g.min_altitude != null || g.max_altitude != null).length;

  return (
    <div style={{ padding: 'var(--space-md)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', flex: 1 }}>
      {/* Header & Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-md)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', backgroundColor: 'var(--status-warning)', borderRadius: '1px' }} />
            <h1 style={{ fontSize: 'var(--text-lg)', textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0 }}>
              Defense Zones & Airspace Perimeters (Stage F5 Engine)
            </h1>
          </div>
          <p className="text-muted text-xs" style={{ margin: '2px 0 0' }}>
            2D bounding boxes and multi-vertex polygon volumes with vertical altitude constraints and automated breach alert evaluation.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          {canCreate && (
            <Button
              variant="primary"
              size="sm"
              onClick={() => {
                setEditingGeofence(null);
                setIsEditorOpen(true);
              }}
            >
              + New Defense Zone
            </Button>
          )}
          <Button variant="secondary" size="sm" onClick={fetchGeofences} isLoading={isLoading}>
            Refresh
          </Button>
        </div>
      </div>

      {error && <ErrorState message={error} onRetry={fetchGeofences} />}

      {successMsg && (
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
            ✓ {successMsg}
          </span>
          <Button variant="ghost" size="sm" onClick={() => setSuccessMsg(null)} style={{ padding: '0 4px', fontSize: '10px' }}>
            ✕
          </Button>
        </div>
      )}

      {/* KPI Overview Cards */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: 'var(--space-sm)' }}>
        <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
          <div className="uppercase-tracking text-muted" style={{ fontSize: '10px' }}>Total Registered Zones</div>
          <div className="font-mono text-xl" style={{ fontWeight: 700, color: 'var(--text-primary)', marginTop: '2px' }}>
            {totalCount}
          </div>
        </Card>

        <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
          <div className="uppercase-tracking text-muted" style={{ fontSize: '10px' }}>Active / Monitored</div>
          <div className="font-mono text-xl" style={{ fontWeight: 700, color: 'var(--color-accent)', marginTop: '2px' }}>
            {activeCount}
          </div>
        </Card>

        <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
          <div className="uppercase-tracking text-muted" style={{ fontSize: '10px' }}>Inclusion Zones</div>
          <div className="font-mono text-xl" style={{ fontWeight: 700, color: 'var(--status-warning)', marginTop: '2px' }}>
            {inclusionCount}
          </div>
        </Card>

        <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
          <div className="uppercase-tracking text-muted" style={{ fontSize: '10px' }}>3D Altitude-Bounded</div>
          <div className="font-mono text-xl" style={{ fontWeight: 700, color: 'var(--status-info)', marginTop: '2px' }}>
            {altitudeBoundedCount}
          </div>
        </Card>
      </div>

      {/* Filter Bar */}
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
        <select
          className="tactical-select font-mono"
          value={statusFilter}
          onChange={(e) => setStatusFilter(e.target.value)}
          style={{ fontSize: '11px' }}
        >
          <option value="">ALL STATUSES</option>
          <option value="ENABLED">ENABLED ONLY</option>
          <option value="DISABLED">DISABLED ONLY</option>
        </select>

        <select
          className="tactical-select font-mono"
          value={ruleFilter}
          onChange={(e) => setRuleFilter(e.target.value)}
          style={{ fontSize: '11px' }}
        >
          <option value="">ALL RULE TYPES</option>
          <option value="EXCLUSION">EXCLUSION (Keep-Out)</option>
          <option value="INCLUSION">INCLUSION (Allowed)</option>
        </select>

        <select
          className="tactical-select font-mono"
          value={typeFilter}
          onChange={(e) => setTypeFilter(e.target.value)}
          style={{ fontSize: '11px' }}
        >
          <option value="">ALL GEOMETRIES</option>
          <option value="bbox">2D BOUNDING BOX</option>
          <option value="polygon">POLYGON PERIMETER</option>
        </select>
      </div>

      {/* Zones Table Card */}
      <Card
        title="Active Airspace Defense Zones"
        badge={<span className="font-mono text-xs text-muted">SHOWING: {filteredGeofences.length}</span>}
        bodyStyle={{ padding: 0 }}
      >
        {isLoading && geofences.length === 0 ? (
          <LoadingState message="Loading defense zones..." />
        ) : filteredGeofences.length === 0 ? (
          <EmptyState title="No Defense Zones Found" description="No geofence perimeters match the query filters." />
        ) : (
          <div className="tactical-table-wrapper" style={{ maxHeight: '560px' }}>
            <table className="tactical-table">
              <thead>
                <tr>
                  <th>Zone Name</th>
                  <th>Status</th>
                  <th>Geometry</th>
                  <th>Rule Type</th>
                  <th>Altitude Range (m)</th>
                  <th>Boundary Geometry Spec</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody>
                {filteredGeofences.map((g) => {
                  const rule = (g.metadata?.rule as string) || 'EXCLUSION';
                  const geomSummary =
                    g.geometry.type === 'bbox'
                      ? `[${g.geometry.min_lat.toFixed(3)}, ${g.geometry.min_lon.toFixed(3)}] to [${g.geometry.max_lat.toFixed(3)}, ${g.geometry.max_lon.toFixed(3)}]`
                      : `${g.geometry.coordinates?.length || 0} vertices polygon`;

                  return (
                    <tr key={g.id}>
                      <td>
                        <div className="font-mono" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                          {g.name}
                        </div>
                        <div className="text-muted text-xs font-mono" title={g.id}>
                          {g.id.length > 18 ? `${g.id.substring(0, 18)}...` : g.id}
                        </div>
                      </td>
                      <td>
                        <StatusBadge
                          status={g.enabled ? 'ACTIVE' : 'CRITICAL'}
                          label={g.enabled ? 'ENABLED' : 'DISABLED'}
                        />
                      </td>
                      <td>
                        <span className="font-mono text-xs" style={{ color: 'var(--color-accent)' }}>
                          {g.geometry.type.toUpperCase()}
                        </span>
                      </td>
                      <td>
                        <span className="font-mono text-xs" style={{ color: rule === 'EXCLUSION' ? 'var(--status-critical)' : 'var(--status-success)' }}>
                          {rule}
                        </span>
                      </td>
                      <td className="font-mono text-xs text-muted">
                        {g.min_altitude != null || g.max_altitude != null
                          ? `${g.min_altitude != null ? `${g.min_altitude}m` : '0m'} - ${g.max_altitude != null ? `${g.max_altitude}m` : '∞'}`
                          : 'Unbounded'}
                      </td>
                      <td className="font-mono text-xs text-muted" title={JSON.stringify(g.geometry)}>
                        {geomSummary}
                      </td>
                      <td>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                          {canUpdate && (
                            <>
                              <Button
                                variant="secondary"
                                size="sm"
                                onClick={() => {
                                  setEditingGeofence(g);
                                  setIsEditorOpen(true);
                                }}
                                style={{ padding: '2px 6px', fontSize: '10px' }}
                              >
                                Edit
                              </Button>
                              <Button
                                variant="ghost"
                                size="sm"
                                onClick={() => handleToggleEnabled(g)}
                                style={{ padding: '2px 6px', fontSize: '10px' }}
                              >
                                {g.enabled ? 'Disable' : 'Enable'}
                              </Button>
                            </>
                          )}
                          {canDelete && (
                            <Button
                              variant="danger"
                              size="sm"
                              onClick={() => setDeletingGeofence(g)}
                              style={{ padding: '2px 6px', fontSize: '10px' }}
                            >
                              Delete
                            </Button>
                          )}
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      {/* Geofence Authoring Editor Modal */}
      <GeofenceEditor
        isOpen={isEditorOpen}
        initialGeofence={editingGeofence}
        onClose={() => {
          setIsEditorOpen(false);
          setEditingGeofence(null);
        }}
        onSave={handleSaveGeofence}
      />

      {/* Two-Step Destructive Deletion Confirmation Modal */}
      {deletingGeofence && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="Confirm Geofence Deletion"
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
                CONFIRM DESTRUCTIVE ZONE DELETION
              </h3>
            </div>

            <p className="text-muted text-xs" style={{ margin: 0, lineHeight: 1.4 }}>
              Are you sure you want to permanently delete defense zone{' '}
              <strong className="font-mono" style={{ color: 'var(--color-accent)' }}>{deletingGeofence.name}</strong>?
              Automated perimeter breach detection and alerts will no longer evaluate against this boundary.
            </p>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '8px', marginTop: '4px' }}>
              <Button variant="ghost" size="sm" onClick={() => setDeletingGeofence(null)} disabled={isDeleting}>
                Cancel
              </Button>
              <Button variant="danger" size="sm" onClick={handleConfirmDelete} isLoading={isDeleting}>
                Permanently Delete Zone
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};
