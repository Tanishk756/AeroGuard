import React, { useCallback, useEffect, useState } from 'react';
import { getSensors } from '../api/sensors';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { LoadingState } from '../components/common/LoadingState';
import { StatusBadge } from '../components/common/StatusBadge';
import { Sensor } from '../types';

export const SensorsPage: React.FC = () => {
  const [sensors, setSensors] = useState<Sensor[]>([]);
  const [total, setTotal] = useState<number>(0);
  const [statusFilter, setStatusFilter] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSensors = useCallback(async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await getSensors({
        status: statusFilter || undefined,
        limit: 50,
      });
      setSensors(res.items);
      setTotal(res.total);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Failed to query sensor registry');
    } finally {
      setIsLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    fetchSensors();
  }, [fetchSensors]);

  return (
    <div style={{ padding: 'var(--space-md)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', flex: 1 }}>
      {/* Header & Filter Controls */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-md)' }}>
        <div>
          <h1 style={{ fontSize: 'var(--text-lg)', textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0 }}>
            Sensor Inventory (Read-Only)
          </h1>
          <p className="text-muted text-xs" style={{ margin: '2px 0 0' }}>
            Registered sensor assets and operational telemetry configurations.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          <select
            className="tactical-select font-mono"
            value={statusFilter}
            onChange={(e) => setStatusFilter(e.target.value)}
          >
            <option value="">ALL STATUSES</option>
            <option value="ACTIVE">ACTIVE</option>
            <option value="INACTIVE">INACTIVE</option>
            <option value="MAINTENANCE">MAINTENANCE</option>
            <option value="DEGRADED">DEGRADED</option>
          </select>

          <Button variant="secondary" size="sm" onClick={fetchSensors} isLoading={isLoading}>
            Refresh
          </Button>
        </div>
      </div>

      {error && <ErrorState message={error} onRetry={fetchSensors} />}

      {/* Sensor Grid / Table */}
      <Card
        title="Registered Sensors"
        badge={<span className="font-mono text-xs text-muted">TOTAL: {total}</span>}
        bodyStyle={{ padding: 0 }}
      >
        {isLoading && sensors.length === 0 ? (
          <LoadingState message="Loading sensor registry..." />
        ) : sensors.length === 0 ? (
          <EmptyState title="No Sensors Found" description="No sensors match the query criteria." />
        ) : (
          <div className="tactical-table-wrapper">
            <table className="tactical-table">
              <thead>
                <tr>
                  <th>Sensor ID</th>
                  <th>Name</th>
                  <th>Modality</th>
                  <th>Source Class</th>
                  <th>Status</th>
                  <th>Range (m)</th>
                  <th>Location</th>
                  <th>Created (UTC)</th>
                </tr>
              </thead>
              <tbody>
                {sensors.map((s) => {
                  const lat = s.configuration_metadata?.latitude;
                  const lon = s.configuration_metadata?.longitude;
                  const range = s.configuration_metadata?.range_meters;

                  return (
                    <tr key={s.id}>
                      <td className="font-mono" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                        {s.id}
                      </td>
                      <td>{s.name}</td>
                      <td className="font-mono text-xs" style={{ color: 'var(--color-accent)' }}>
                        {s.source_type.toUpperCase()}
                      </td>
                      <td>
                        <StatusBadge status={s.source_class} />
                      </td>
                      <td>
                        <StatusBadge status={s.status} />
                      </td>
                      <td className="font-mono text-xs">
                        {range != null ? `${range.toLocaleString()} m` : 'N/A'}
                      </td>
                      <td className="font-mono text-xs text-muted">
                        {lat != null && lon != null ? `${Number(lat).toFixed(4)}°, ${Number(lon).toFixed(4)}°` : 'Stationary / Unset'}
                      </td>
                      <td className="font-mono text-xs text-muted">
                        {s.created_at.substring(0, 10)}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        )}
      </Card>
    </div>
  );
};
