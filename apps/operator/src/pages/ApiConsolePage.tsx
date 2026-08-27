import React, { useMemo } from 'react';
import { useSearchParams } from 'react-router-dom';
import { API_CATALOG } from '../api/developer';
import { ApiCatalog } from '../components/developer/ApiCatalog';
import { DetectionWorkbench } from '../components/developer/DetectionWorkbench';
import { RequestDispatcher } from '../components/developer/RequestDispatcher';
import { SchemaViewer } from '../components/developer/SchemaViewer';
import { useAuth } from '../context/AuthContext';
import { ApiEndpoint } from '../types/developer';

type ConsoleTab = 'catalog' | 'dispatcher' | 'workbench' | 'schemas';

export const ApiConsolePage: React.FC = () => {
  const [searchParams, setSearchParams] = useSearchParams();
  const { user } = useAuth();

  const activeTab: ConsoleTab = useMemo(() => {
    const tabParam = searchParams.get('tab');
    if (tabParam === 'dispatcher' || tabParam === 'workbench' || tabParam === 'schemas') {
      return tabParam;
    }
    return 'catalog';
  }, [searchParams]);

  const endpointParam = searchParams.get('endpoint');
  const sensorIdParam = searchParams.get('sensor_id') || undefined;

  const selectedEndpoint: ApiEndpoint = useMemo(() => {
    if (endpointParam) {
      const match = API_CATALOG.find((e: ApiEndpoint) => e.id === endpointParam);
      if (match) return match;
    }
    return API_CATALOG[0];
  }, [endpointParam]);

  const handleTabChange = (tab: ConsoleTab) => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('tab', tab);
    setSearchParams(nextParams);
  };

  const handleSelectEndpoint = (endpoint: ApiEndpoint) => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('tab', 'dispatcher');
    nextParams.set('endpoint', endpoint.id);
    setSearchParams(nextParams);
  };

  const handleEndpointChanged = (endpoint: ApiEndpoint) => {
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set('endpoint', endpoint.id);
    setSearchParams(nextParams);
  };

  return (
    <div style={{ padding: 'var(--space-md)', display: 'flex', flexDirection: 'column', gap: 'var(--space-md)', flex: 1 }}>
      {/* Page Header */}
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 'var(--space-md)' }}>
        <div>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span style={{ width: '8px', height: '8px', backgroundColor: 'var(--color-accent)', borderRadius: '1px' }} />
            <h1 style={{ fontSize: 'var(--text-lg)', textTransform: 'uppercase', letterSpacing: '0.06em', margin: 0 }}>
              Developer & API Console
            </h1>
          </div>
          <p className="text-muted text-xs" style={{ margin: '2px 0 0' }}>
            REST API catalog, interactive request dispatcher, synthetic sensor detection workbench, and contract specifications.
          </p>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)' }}>
          <span className="font-mono text-xs text-muted">
            SESSION: {user?.username || 'GUEST'} • {user?.roles?.join(', ') || 'VIEWER'}
          </span>
        </div>
      </div>

      {/* Navigation Sub-Tabs */}
      <div
        style={{
          display: 'flex',
          gap: 'var(--space-xs)',
          borderBottom: '1px solid var(--border-medium)',
          paddingBottom: '2px',
        }}
      >
        <button
          onClick={() => handleTabChange('catalog')}
          className="tactical-btn"
          style={{
            padding: '6px 14px',
            fontSize: 'var(--text-sm)',
            backgroundColor: activeTab === 'catalog' ? 'var(--bg-surface-active)' : 'transparent',
            borderBottom: activeTab === 'catalog' ? '2px solid var(--color-accent)' : '2px solid transparent',
            color: activeTab === 'catalog' ? 'var(--color-accent)' : 'var(--text-secondary)',
            fontWeight: activeTab === 'catalog' ? 600 : 400,
            borderRadius: 'var(--radius-sm) var(--radius-sm) 0 0',
          }}
        >
          📂 API Catalog ({API_CATALOG.length})
        </button>

        <button
          onClick={() => handleTabChange('dispatcher')}
          className="tactical-btn"
          style={{
            padding: '6px 14px',
            fontSize: 'var(--text-sm)',
            backgroundColor: activeTab === 'dispatcher' ? 'var(--bg-surface-active)' : 'transparent',
            borderBottom: activeTab === 'dispatcher' ? '2px solid var(--color-accent)' : '2px solid transparent',
            color: activeTab === 'dispatcher' ? 'var(--color-accent)' : 'var(--text-secondary)',
            fontWeight: activeTab === 'dispatcher' ? 600 : 400,
            borderRadius: 'var(--radius-sm) var(--radius-sm) 0 0',
          }}
        >
          ⚡ Request Dispatcher
        </button>

        <button
          onClick={() => handleTabChange('workbench')}
          className="tactical-btn"
          style={{
            padding: '6px 14px',
            fontSize: 'var(--text-sm)',
            backgroundColor: activeTab === 'workbench' ? 'var(--bg-surface-active)' : 'transparent',
            borderBottom: activeTab === 'workbench' ? '2px solid var(--color-accent)' : '2px solid transparent',
            color: activeTab === 'workbench' ? 'var(--color-accent)' : 'var(--text-secondary)',
            fontWeight: activeTab === 'workbench' ? 600 : 400,
            borderRadius: 'var(--radius-sm) var(--radius-sm) 0 0',
          }}
        >
          🛰️ Ingestion Workbench
        </button>

        <button
          onClick={() => handleTabChange('schemas')}
          className="tactical-btn"
          style={{
            padding: '6px 14px',
            fontSize: 'var(--text-sm)',
            backgroundColor: activeTab === 'schemas' ? 'var(--bg-surface-active)' : 'transparent',
            borderBottom: activeTab === 'schemas' ? '2px solid var(--color-accent)' : '2px solid transparent',
            color: activeTab === 'schemas' ? 'var(--color-accent)' : 'var(--text-secondary)',
            fontWeight: activeTab === 'schemas' ? 600 : 400,
            borderRadius: 'var(--radius-sm) var(--radius-sm) 0 0',
          }}
        >
          📋 Data Contracts
        </button>
      </div>

      {/* Tab Panels */}
      {activeTab === 'catalog' && (
        <ApiCatalog
          onSelectEndpoint={handleSelectEndpoint}
          selectedEndpointId={selectedEndpoint.id}
        />
      )}

      {activeTab === 'dispatcher' && (
        <RequestDispatcher
          initialEndpoint={selectedEndpoint}
          onEndpointChanged={handleEndpointChanged}
        />
      )}

      {activeTab === 'workbench' && (
        <DetectionWorkbench initialSensorId={sensorIdParam} />
      )}

      {activeTab === 'schemas' && (
        <SchemaViewer />
      )}
    </div>
  );
};
