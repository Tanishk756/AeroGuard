import React, { useCallback, useEffect, useState } from 'react';
import { getAuditEvents } from '../api/audit';
import { Button } from '../components/common/Button';
import { Card } from '../components/common/Card';
import { EmptyState } from '../components/common/EmptyState';
import { ErrorState } from '../components/common/ErrorState';
import { LoadingState } from '../components/common/LoadingState';
import { StatusBadge } from '../components/common/StatusBadge';
import { AuditEventInspector } from '../components/inspector/AuditEventInspector';
import { AuditEvent, AuditFilterParams } from '../types';

export const AuditLogPage: React.FC = () => {
  const [events, setEvents] = useState<AuditEvent[]>([]);
  const [nextCursor, setNextCursor] = useState<string | null>(null);
  const [cursorHistory, setCursorHistory] = useState<string[]>([]);
  const [selectedEvent, setSelectedEvent] = useState<AuditEvent | null>(null);

  // Filter state
  const [eventTypeFilter, setEventTypeFilter] = useState<string>('');
  const [resultFilter, setResultFilter] = useState<string>('');
  const [actorIdFilter, setActorIdFilter] = useState<string>('');
  const [targetTypeFilter, setTargetTypeFilter] = useState<string>('');
  const [targetIdFilter, setTargetIdFilter] = useState<string>('');
  const [permissionFilter, setPermissionFilter] = useState<string>('');
  const [dateFrom, setDateFrom] = useState<string>('');
  const [dateTo, setDateTo] = useState<string>('');
  const [limit, setLimit] = useState<number>(50);

  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const fetchEvents = useCallback(
    async (cursor?: string) => {
      setIsLoading(true);
      setError(null);
      try {
        const params: AuditFilterParams = {
          event_type: eventTypeFilter || undefined,
          result: resultFilter || undefined,
          actor_id: actorIdFilter.trim() || undefined,
          target_type: targetTypeFilter || undefined,
          target_id: targetIdFilter.trim() || undefined,
          permission: permissionFilter.trim() || undefined,
          date_from: dateFrom ? new Date(dateFrom).toISOString() : undefined,
          date_to: dateTo ? new Date(dateTo).toISOString() : undefined,
          cursor: cursor || undefined,
          limit,
        };

        const res = await getAuditEvents(params);
        setEvents(res.items || []);
        setNextCursor(res.next_cursor || null);

        if (res.items && res.items.length > 0) {
          if (!selectedEvent || !res.items.some((e) => e.id === selectedEvent.id)) {
            setSelectedEvent(res.items[0]);
          }
        } else {
          setSelectedEvent(null);
        }
      } catch (err: unknown) {
        setError(err instanceof Error ? err.message : 'Failed to query audit event log');
      } finally {
        setIsLoading(false);
      }
    },
    [
      eventTypeFilter,
      resultFilter,
      actorIdFilter,
      targetTypeFilter,
      targetIdFilter,
      permissionFilter,
      dateFrom,
      dateTo,
      limit,
      selectedEvent,
    ]
  );

  // Initial load or filter change reset
  const handleApplyFilters = () => {
    setCursorHistory([]);
    fetchEvents(undefined);
  };

  useEffect(() => {
    handleApplyFilters();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [eventTypeFilter, resultFilter, targetTypeFilter, limit]);

  const handleNextPage = () => {
    if (!nextCursor) return;
    const currentCursor = cursorHistory[cursorHistory.length - 1] || '';
    setCursorHistory((prev) => [...prev, nextCursor]);
    fetchEvents(nextCursor);
  };

  const handlePreviousPage = () => {
    if (cursorHistory.length === 0) return;
    const newHistory = [...cursorHistory];
    newHistory.pop(); // remove current cursor
    const previousCursor = newHistory[newHistory.length - 1] || undefined;
    setCursorHistory(newHistory);
    fetchEvents(previousCursor);
  };

  const handleResetFilters = () => {
    setEventTypeFilter('');
    setResultFilter('');
    setActorIdFilter('');
    setTargetTypeFilter('');
    setTargetIdFilter('');
    setPermissionFilter('');
    setDateFrom('');
    setDateTo('');
    setCursorHistory([]);
    fetchEvents(undefined);
  };

  const setTimePreset = (hours: number) => {
    const now = new Date();
    const past = new Date(now.getTime() - hours * 60 * 60 * 1000);
    setDateFrom(past.toISOString().substring(0, 16));
    setDateTo(now.toISOString().substring(0, 16));
    setCursorHistory([]);
  };

  return (
    <div style={{ padding: 'var(--space-md)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', flex: 1 }}>
      {/* Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-md)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', backgroundColor: 'var(--color-accent)', borderRadius: '1px' }} />
            <h1 style={{ fontSize: 'var(--text-lg)', textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0 }}>
              Security Audit & Governance Explorer (Stage E Engine)
            </h1>
          </div>
          <p className="text-muted text-xs" style={{ margin: '2px 0 0' }}>
            Append-only, immutable audit trail recording all security actions, authentication events, and governance mutations.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          <Button variant="secondary" size="sm" onClick={() => fetchEvents(cursorHistory[cursorHistory.length - 1])} isLoading={isLoading}>
            Refresh Audit Feed
          </Button>
        </div>
      </div>

      {error && <ErrorState message={error} onRetry={() => fetchEvents(cursorHistory[cursorHistory.length - 1])} />}

      {/* Filter Toolbar Card */}
      <Card title="Audit Event Filters & Cursor Window">
        <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-sm)' }}>
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))', gap: 'var(--space-xs)', alignItems: 'flex-end' }}>
            {/* Event Type Select */}
            <div>
              <label className="text-muted text-xs uppercase-tracking" style={{ display: 'block', marginBottom: '2px' }}>Event Type</label>
              <select
                className="tactical-select font-mono"
                value={eventTypeFilter}
                onChange={(e) => setEventTypeFilter(e.target.value)}
                style={{ width: '100%', fontSize: '11px' }}
              >
                <option value="">ALL EVENT TYPES</option>
                <option value="LOGIN_SUCCESS">LOGIN_SUCCESS</option>
                <option value="LOGIN_FAILURE">LOGIN_FAILURE</option>
                <option value="LOGOUT">LOGOUT</option>
                <option value="SESSION_CREATED">SESSION_CREATED</option>
                <option value="SESSION_REVOKED">SESSION_REVOKED</option>
                <option value="ROLE_CREATED">ROLE_CREATED</option>
                <option value="ROLE_UPDATED">ROLE_UPDATED</option>
                <option value="ROLE_DELETED">ROLE_DELETED</option>
                <option value="ROLE_ASSIGNED">ROLE_ASSIGNED</option>
                <option value="ROLE_REVOKED">ROLE_REVOKED</option>
                <option value="PERMISSION_ASSIGNED">PERMISSION_ASSIGNED</option>
                <option value="PERMISSION_REVOKED">PERMISSION_REVOKED</option>
              </select>
            </div>

            {/* Outcome Result Select */}
            <div>
              <label className="text-muted text-xs uppercase-tracking" style={{ display: 'block', marginBottom: '2px' }}>Result</label>
              <select
                className="tactical-select font-mono"
                value={resultFilter}
                onChange={(e) => setResultFilter(e.target.value)}
                style={{ width: '100%', fontSize: '11px' }}
              >
                <option value="">ALL RESULTS</option>
                <option value="SUCCESS">SUCCESS</option>
                <option value="FAILURE">FAILURE</option>
              </select>
            </div>

            {/* Target Type Select */}
            <div>
              <label className="text-muted text-xs uppercase-tracking" style={{ display: 'block', marginBottom: '2px' }}>Target Type</label>
              <select
                className="tactical-select font-mono"
                value={targetTypeFilter}
                onChange={(e) => setTargetTypeFilter(e.target.value)}
                style={{ width: '100%', fontSize: '11px' }}
              >
                <option value="">ALL TARGETS</option>
                <option value="user">User</option>
                <option value="role">Role</option>
                <option value="session">Session</option>
                <option value="sensor">Sensor</option>
                <option value="track">Track</option>
              </select>
            </div>

            {/* Actor User ID Search */}
            <div>
              <label className="text-muted text-xs uppercase-tracking" style={{ display: 'block', marginBottom: '2px' }}>Actor User ID</label>
              <input
                type="text"
                className="tactical-input font-mono"
                value={actorIdFilter}
                onChange={(e) => setActorIdFilter(e.target.value)}
                placeholder="Filter by Actor ID..."
                style={{ width: '100%', fontSize: '11px' }}
              />
            </div>

            {/* Date From */}
            <div>
              <label className="text-muted text-xs uppercase-tracking" style={{ display: 'block', marginBottom: '2px' }}>Date From (UTC)</label>
              <input
                type="datetime-local"
                className="tactical-input font-mono"
                value={dateFrom}
                onChange={(e) => setDateFrom(e.target.value)}
                style={{ width: '100%', fontSize: '11px' }}
              />
            </div>

            {/* Date To */}
            <div>
              <label className="text-muted text-xs uppercase-tracking" style={{ display: 'block', marginBottom: '2px' }}>Date To (UTC)</label>
              <input
                type="datetime-local"
                className="tactical-input font-mono"
                value={dateTo}
                onChange={(e) => setDateTo(e.target.value)}
                style={{ width: '100%', fontSize: '11px' }}
              />
            </div>
          </div>

          {/* Quick Presets & Actions */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-xs)' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
              <span className="text-muted text-xs font-mono">Presets:</span>
              <button onClick={() => setTimePreset(1)} className="tactical-btn font-mono" style={{ padding: '2px 6px', fontSize: '10px' }}>1h</button>
              <button onClick={() => setTimePreset(6)} className="tactical-btn font-mono" style={{ padding: '2px 6px', fontSize: '10px' }}>6h</button>
              <button onClick={() => setTimePreset(24)} className="tactical-btn font-mono" style={{ padding: '2px 6px', fontSize: '10px' }}>24h</button>
              <button onClick={() => setTimePreset(168)} className="tactical-btn font-mono" style={{ padding: '2px 6px', fontSize: '10px' }}>7d</button>
              <button onClick={handleResetFilters} className="tactical-btn font-mono" style={{ padding: '2px 6px', fontSize: '10px', color: 'var(--text-muted)' }}>Reset Filters</button>
            </div>

            <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
              <Button variant="primary" size="sm" onClick={handleApplyFilters} isLoading={isLoading} style={{ padding: '3px 8px', fontSize: '11px' }}>
                Apply Query
              </Button>
            </div>
          </div>
        </div>
      </Card>

      {/* Main Split Layout: Audit Table + Context Inspector */}
      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(420px, 1.8fr) minmax(320px, 1.1fr)', gap: 'var(--space-md)', flex: 1 }}>
        {/* Audit Events Table */}
        <Card
          title="Immutable Audit Event Ledger"
          badge={
            <span className="font-mono text-xs text-muted">
              PAGE {cursorHistory.length + 1} • EVENTS: {events.length}
            </span>
          }
          bodyStyle={{ padding: 0 }}
        >
          {isLoading && events.length === 0 ? (
            <LoadingState message="Executing cursor audit query..." />
          ) : events.length === 0 ? (
            <EmptyState title="No Audit Records Found" description="Zero audit events match the selected filters." />
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
              <div className="tactical-table-wrapper" style={{ maxHeight: '520px', flex: 1 }}>
                <table className="tactical-table">
                  <thead>
                    <tr>
                      <th>Time (UTC)</th>
                      <th>Event Type</th>
                      <th>Result</th>
                      <th>Action</th>
                      <th>Actor ID</th>
                      <th>Target</th>
                    </tr>
                  </thead>
                  <tbody>
                    {events.map((ev) => {
                      const isSelected = selectedEvent?.id === ev.id;
                      const isSuccess = ev.result.toUpperCase() === 'SUCCESS';

                      return (
                        <tr
                          key={ev.id}
                          onClick={() => setSelectedEvent(ev)}
                          style={{
                            cursor: 'pointer',
                            backgroundColor: isSelected ? 'var(--bg-surface-active)' : undefined,
                          }}
                        >
                          <td className="font-mono text-xs text-muted">
                            {ev.timestamp ? ev.timestamp.substring(11, 19) : '-'}
                          </td>
                          <td className="font-mono text-xs" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                            {ev.event_type}
                          </td>
                          <td>
                            <StatusBadge
                              status={isSuccess ? 'ACTIVE' : 'CRITICAL'}
                              label={ev.result}
                            />
                          </td>
                          <td className="font-mono text-xs">{ev.action}</td>
                          <td className="font-mono text-xs text-muted" title={ev.actor_user_id || 'System'}>
                            {ev.actor_user_id ? `${ev.actor_user_id.substring(0, 10)}...` : 'System'}
                          </td>
                          <td className="font-mono text-xs text-muted">
                            {ev.target_type ? `${ev.target_type}:${(ev.target_id || '').substring(0, 8)}` : '-'}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              </div>

              {/* Cursor Pagination Navigation Bar */}
              <div
                style={{
                  padding: '6px 12px',
                  borderTop: '1px solid var(--border-medium)',
                  backgroundColor: 'var(--bg-canvas)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  fontSize: '11px',
                }}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                  <span className="font-mono text-muted">Limit:</span>
                  <select
                    className="tactical-select font-mono"
                    value={limit}
                    onChange={(e) => setLimit(Number(e.target.value))}
                    style={{ padding: '2px 4px', fontSize: '10px' }}
                  >
                    <option value={25}>25 / page</option>
                    <option value={50}>50 / page</option>
                    <option value={100}>100 / page</option>
                  </select>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)' }}>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handlePreviousPage}
                    disabled={cursorHistory.length === 0 || isLoading}
                    style={{ padding: '3px 8px', fontSize: '11px' }}
                  >
                    ← Previous Page
                  </Button>
                  <Button
                    variant="secondary"
                    size="sm"
                    onClick={handleNextPage}
                    disabled={!nextCursor || isLoading}
                    style={{ padding: '3px 8px', fontSize: '11px' }}
                  >
                    Next Page →
                  </Button>
                </div>
              </div>
            </div>
          )}
        </Card>

        {/* Selected Event Context Inspector */}
        <div>
          {selectedEvent ? (
            <AuditEventInspector
              event={selectedEvent}
              onClose={() => setSelectedEvent(null)}
              onFilterByActor={(actorId) => {
                setActorIdFilter(actorId);
                setCursorHistory([]);
                fetchEvents(undefined);
              }}
              onFilterByTarget={(targetType, targetId) => {
                setTargetTypeFilter(targetType);
                setTargetIdFilter(targetId);
                setCursorHistory([]);
                fetchEvents(undefined);
              }}
            />
          ) : (
            <Card title="Audit Event Detail">
              <EmptyState title="No Event Selected" description="Select any row from the audit table to inspect full metadata, correlation IDs, and security context." />
            </Card>
          )}
        </div>
      </div>
    </div>
  );
};
