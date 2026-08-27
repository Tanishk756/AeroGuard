import React, { useMemo, useState } from 'react';
import { API_CATALOG, API_DOMAINS, generateCurlCommand } from '../../api/developer';
import { Button } from '../common/Button';
import { Card } from '../common/Card';
import { StatusBadge } from '../common/StatusBadge';
import { useAuth } from '../../context/AuthContext';
import { ApiDomain, ApiEndpoint, HttpMethod } from '../../types/developer';

interface ApiCatalogProps {
  onSelectEndpoint: (endpoint: ApiEndpoint) => void;
  selectedEndpointId?: string;
}

const METHOD_COLORS: Record<HttpMethod, { bg: string; text: string; border: string }> = {
  GET: { bg: 'rgba(56, 189, 248, 0.15)', text: '#38bdf8', border: 'rgba(56, 189, 248, 0.4)' },
  POST: { bg: 'rgba(74, 222, 128, 0.15)', text: '#4ade80', border: 'rgba(74, 222, 128, 0.4)' },
  PUT: { bg: 'rgba(251, 191, 36, 0.15)', text: '#fbbf24', border: 'rgba(251, 191, 36, 0.4)' },
  PATCH: { bg: 'rgba(249, 115, 22, 0.15)', text: '#f97316', border: 'rgba(249, 115, 22, 0.4)' },
  DELETE: { bg: 'rgba(248, 113, 113, 0.15)', text: '#f87171', border: 'rgba(248, 113, 113, 0.4)' },
};

export const ApiCatalog: React.FC<ApiCatalogProps> = ({ onSelectEndpoint, selectedEndpointId }) => {
  const { hasPermission, hasAnyPermission } = useAuth();
  const [selectedDomain, setSelectedDomain] = useState<string>('ALL');
  const [searchQuery, setSearchQuery] = useState<string>('');
  const [copiedId, setCopiedId] = useState<string | null>(null);

  const filteredEndpoints = useMemo(() => {
    return API_CATALOG.filter((ep) => {
      if (selectedDomain !== 'ALL' && ep.domain !== selectedDomain) {
        return false;
      }
      if (searchQuery.trim()) {
        const q = searchQuery.toLowerCase();
        const matchName = ep.name.toLowerCase().includes(q);
        const matchPath = ep.path.toLowerCase().includes(q);
        const matchDesc = ep.description.toLowerCase().includes(q);
        const matchMethod = ep.method.toLowerCase().includes(q);
        const matchDomain = ep.domain.toLowerCase().includes(q);
        return matchName || matchPath || matchDesc || matchMethod || matchDomain;
      }
      return true;
    });
  }, [selectedDomain, searchQuery]);

  const handleCopyCurl = (e: React.MouseEvent, ep: ApiEndpoint) => {
    e.stopPropagation();
    const cmd = generateCurlCommand(ep.method, `http://localhost:8000/api/v1${ep.path}`, {
      'Content-Type': 'application/json',
    }, ep.requestBodyTemplate);
    navigator.clipboard.writeText(cmd);
    setCopiedId(ep.id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const checkUserAccess = (ep: ApiEndpoint) => {
    if (ep.requiredPermission) {
      return hasPermission(ep.requiredPermission);
    }
    if (ep.requiredAnyPermissions) {
      return hasAnyPermission(ep.requiredAnyPermissions);
    }
    return true; // Public
  };

  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 'var(--space-md)' }}>
      {/* Search & Domain Filter Toolbar */}
      <Card bodyStyle={{ padding: 'var(--space-sm) var(--space-md)' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 'var(--space-md)', alignItems: 'center', justifyContent: 'space-between' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-sm)', flex: 1, minWidth: '240px' }}>
            <span style={{ color: 'var(--text-muted)', fontSize: '14px' }}>🔍</span>
            <input
              type="text"
              className="tactical-input"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Filter by endpoint path, method, name, or parameter..."
              style={{ width: '100%' }}
            />
            {searchQuery && (
              <button
                className="tactical-btn"
                onClick={() => setSearchQuery('')}
                style={{ padding: '4px 8px', fontSize: '11px', backgroundColor: 'transparent' }}
              >
                Clear
              </button>
            )}
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-xs)', flexWrap: 'wrap' }}>
            <span className="uppercase-tracking text-muted" style={{ fontSize: '10px', marginRight: '4px' }}>
              Domain:
            </span>
            <button
              onClick={() => setSelectedDomain('ALL')}
              className="tactical-btn"
              style={{
                padding: '4px 10px',
                fontSize: '11px',
                backgroundColor: selectedDomain === 'ALL' ? 'var(--color-accent)' : 'var(--bg-canvas)',
                color: selectedDomain === 'ALL' ? '#000' : 'var(--text-secondary)',
                fontWeight: selectedDomain === 'ALL' ? 700 : 400,
              }}
            >
              All ({API_CATALOG.length})
            </button>
            {API_DOMAINS.map((domain) => {
              const count = API_CATALOG.filter((e) => e.domain === domain).length;
              const isSelected = selectedDomain === domain;
              return (
                <button
                  key={domain}
                  onClick={() => setSelectedDomain(domain)}
                  className="tactical-btn"
                  style={{
                    padding: '4px 8px',
                    fontSize: '11px',
                    backgroundColor: isSelected ? 'var(--color-accent)' : 'var(--bg-canvas)',
                    color: isSelected ? '#000' : 'var(--text-secondary)',
                    fontWeight: isSelected ? 700 : 400,
                  }}
                >
                  {domain} ({count})
                </button>
              );
            })}
          </div>
        </div>
      </Card>

      {/* Catalog Table */}
      <Card title={`API Catalog Directory (${filteredEndpoints.length} Endpoints)`}>
        {filteredEndpoints.length === 0 ? (
          <div style={{ padding: 'var(--space-xl)', textAlign: 'center', color: 'var(--text-muted)' }}>
            No endpoints matched the search query or domain filter.
          </div>
        ) : (
          <div style={{ overflowX: 'auto' }}>
            <table className="tactical-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr>
                  <th style={{ width: '90px' }}>METHOD</th>
                  <th>ENDPOINT PATH & NAME</th>
                  <th>DOMAIN</th>
                  <th>REQUIRED RBAC AUTHORITY</th>
                  <th style={{ width: '180px', textAlign: 'right' }}>ACTIONS</th>
                </tr>
              </thead>
              <tbody>
                {filteredEndpoints.map((ep) => {
                  const methodStyle = METHOD_COLORS[ep.method];
                  const hasAccess = checkUserAccess(ep);
                  const isSelected = selectedEndpointId === ep.id;

                  return (
                    <tr
                      key={ep.id}
                      onClick={() => onSelectEndpoint(ep)}
                      style={{
                        cursor: 'pointer',
                        backgroundColor: isSelected ? 'var(--bg-surface-active)' : undefined,
                        borderLeft: isSelected ? '3px solid var(--color-accent)' : '3px solid transparent',
                      }}
                    >
                      <td>
                        <span
                          className="font-mono text-xs"
                          style={{
                            display: 'inline-block',
                            padding: '3px 8px',
                            borderRadius: '3px',
                            fontWeight: 700,
                            backgroundColor: methodStyle.bg,
                            color: methodStyle.text,
                            border: `1px solid ${methodStyle.border}`,
                          }}
                        >
                          {ep.method}
                        </span>
                      </td>
                      <td>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span className="font-mono text-sm" style={{ fontWeight: 600, color: 'var(--text-primary)' }}>
                              {ep.path}
                            </span>
                            {ep.pathParams && (
                              <span className="font-mono text-xs text-muted" title="Has path parameters">
                                [{ep.pathParams.map((p) => `{${p.name}}`).join(', ')}]
                              </span>
                            )}
                          </div>
                          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--text-muted)' }}>
                            {ep.name} — {ep.description}
                          </span>
                        </div>
                      </td>
                      <td>
                        <span className="uppercase-tracking" style={{ fontSize: '10px', color: 'var(--text-secondary)' }}>
                          {ep.domain}
                        </span>
                      </td>
                      <td>
                        {ep.requiredPermission ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span
                              className="font-mono text-xs"
                              style={{
                                padding: '2px 6px',
                                borderRadius: '3px',
                                backgroundColor: 'var(--bg-canvas)',
                                border: '1px solid var(--border-subtle)',
                                color: hasAccess ? 'var(--status-active)' : 'var(--status-critical)',
                              }}
                            >
                              {ep.requiredPermission}
                            </span>
                            <StatusBadge
                              status={hasAccess ? 'ACTIVE' : 'CRITICAL'}
                              label={hasAccess ? 'AUTHORIZED' : 'DENIED'}
                            />
                          </div>
                        ) : ep.requiredAnyPermissions ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                            <span
                              className="font-mono text-xs"
                              style={{
                                padding: '2px 6px',
                                borderRadius: '3px',
                                backgroundColor: 'var(--bg-canvas)',
                                border: '1px solid var(--border-subtle)',
                                color: hasAccess ? 'var(--status-active)' : 'var(--status-critical)',
                              }}
                              title={ep.requiredAnyPermissions.join(', ')}
                            >
                              ANY({ep.requiredAnyPermissions.length})
                            </span>
                            <StatusBadge
                              status={hasAccess ? 'ACTIVE' : 'CRITICAL'}
                              label={hasAccess ? 'AUTHORIZED' : 'DENIED'}
                            />
                          </div>
                        ) : (
                          <span className="font-mono text-xs" style={{ color: 'var(--status-active)' }}>
                            PUBLIC / AUTH
                          </span>
                        )}
                      </td>
                      <td style={{ textAlign: 'right' }}>
                        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end', gap: '6px' }}>
                          <button
                            type="button"
                            className="tactical-btn"
                            onClick={(e) => handleCopyCurl(e, ep)}
                            style={{ padding: '3px 8px', fontSize: '11px' }}
                            title="Copy cURL CLI snippet"
                          >
                            {copiedId === ep.id ? '✓ Copied' : 'cURL'}
                          </button>
                          <Button
                            variant="secondary"
                            size="sm"
                            onClick={() => onSelectEndpoint(ep)}
                          >
                            Dispatch →
                          </Button>
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
    </div>
  );
};
