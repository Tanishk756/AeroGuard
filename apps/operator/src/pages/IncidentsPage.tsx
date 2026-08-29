/**
 * AeroGuard Incident Management Workspace Page
 * Stage IM1-E: Operator Incident Workspace
 */

import React, { useState } from 'react';
import { CreateIncidentModal } from '../components/incidents/CreateIncidentModal';
import { IncidentDetail } from '../components/incidents/IncidentDetail';
import { IncidentList } from '../components/incidents/IncidentList';
import { useAuth } from '../context/AuthContext';
import { useIncidents } from '../hooks/useIncidents';

export const IncidentsPage: React.FC = () => {
  const { hasPermission } = useAuth();
  const canCreate = hasPermission('incidents.create');

  const {
    incidents,
    selectedIncidentId,
    selectedIncident,
    timeline,
    isLoading,
    isDetailLoading,
    isTimelineLoading,
    isMutating,
    error,
    filters,
    setFilters,
    selectIncident,
    refreshList,
    createIncident,
    acknowledgeIncident,
    assignIncident,
    triageIncident,
    escalateIncident,
    deEscalateIncident,
    resolveIncident,
    closeIncident,
    addNote,
    logDefensiveAction,
  } = useIncidents();

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: 'calc(100vh - 56px)',
        overflow: 'hidden',
        boxSizing: 'border-box',
      }}
    >
      {/* Top Banner / Error notification */}
      {error && (
        <div
          role="alert"
          style={{
            padding: '8px 16px',
            backgroundColor: 'rgba(239, 68, 68, 0.15)',
            borderBottom: '1px solid var(--status-critical, #ef4444)',
            color: '#fca5a5',
            fontSize: '12px',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
          }}
          className="font-mono"
        >
          <span>⚠ {error}</span>
          <button
            type="button"
            className="btn btn-secondary btn-sm"
            onClick={() => refreshList()}
            style={{ padding: '2px 6px', fontSize: '11px' }}
          >
            ↻ Retry
          </button>
        </div>
      )}

      {/* Split Workspace View */}
      <div
        style={{
          display: 'grid',
          gridTemplateColumns: '360px 1fr',
          flex: 1,
          overflow: 'hidden',
        }}
      >
        {/* Left Column: Incident List */}
        <IncidentList
          incidents={incidents}
          selectedId={selectedIncidentId}
          onSelect={selectIncident}
          isLoading={isLoading}
          filters={filters}
          onFilterChange={setFilters}
          onOpenCreateModal={() => setIsCreateModalOpen(true)}
          canCreate={canCreate}
        />

        {/* Right Column: Incident Detail & Timeline */}
        <IncidentDetail
          incident={selectedIncident}
          timeline={timeline}
          isLoading={isDetailLoading}
          isTimelineLoading={isTimelineLoading}
          isMutating={isMutating}
          onAcknowledge={acknowledgeIncident}
          onAssign={assignIncident}
          onTriage={triageIncident}
          onEscalate={escalateIncident}
          onDeEscalate={deEscalateIncident}
          onResolve={resolveIncident}
          onClose={closeIncident}
          onAddNote={addNote}
          onLogAction={logDefensiveAction}
        />
      </div>

      {/* Create Incident Modal */}
      <CreateIncidentModal
        isOpen={isCreateModalOpen}
        onClose={() => setIsCreateModalOpen(false)}
        onSubmit={async (data) => {
          await createIncident(data);
        }}
        isSubmitting={isMutating}
      />
    </div>
  );
};
