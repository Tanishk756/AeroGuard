/**
 * AeroGuard Incident Management Workspace Page
 * Stage IM1-E: Operator Incident Workspace
 */

import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { CreateIncidentModal } from '../components/incidents/CreateIncidentModal';
import { IncidentDetail } from '../components/incidents/IncidentDetail';
import { IncidentExportModal } from '../components/incidents/IncidentExportModal';
import { IncidentList } from '../components/incidents/IncidentList';
import { useAuth } from '../context/AuthContext';
import { useIncidents } from '../hooks/useIncidents';

export const IncidentsPage: React.FC = () => {
  const [searchParams] = useSearchParams();
  const paramIncidentId = searchParams.get('selected_id') || searchParams.get('incident_id');
  const { hasPermission } = useAuth();
  const canCreate = hasPermission('incidents.create');
  const canExport = hasPermission('incidents.export');

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

  useEffect(() => {
    if (paramIncidentId && paramIncidentId !== selectedIncidentId) {
      selectIncident(paramIncidentId);
    }
  }, [paramIncidentId, selectIncident, selectedIncidentId]);

  const [isCreateModalOpen, setIsCreateModalOpen] = useState(false);
  const [isExportModalOpen, setIsExportModalOpen] = useState(false);

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
          onOpenExportModal={() => setIsExportModalOpen(true)}
          canExport={canExport}
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

      {/* Incident Export Modal */}
      <IncidentExportModal
        isOpen={isExportModalOpen}
        onClose={() => setIsExportModalOpen(false)}
      />
    </div>
  );
};
